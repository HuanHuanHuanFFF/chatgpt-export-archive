import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import uuid
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "archive.py"
spec = importlib.util.spec_from_file_location("archive", SCRIPT)
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.root = SCRIPT.parent / "tests" / ".runs" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.original_home = archive.HOME
        archive.HOME = self.root
        self.source = self.root / "source"
        self.source.mkdir()
        def node(key, parent, text, role="user", kind="text"):
            content = {"content_type": kind, "parts": [text]}
            if kind == "thoughts":
                content = {"content_type": kind, "thoughts": [{"summary": "思考", "content": text}]}
            return {"id": key, "parent": parent, "message": {"id": key, "author": {"role": role}, "create_time": 1729000000, "content": content}}
        self.conversation = {"id": "../../CON/unsafe", "title": "测试 <script>alert(1)</script>", "create_time": 1729000000, "current_node": "reply", "mapping": {
            "root": {"id": "root", "parent": None, "message": None},
            "question": node("question", "root", "我的向量数据库想法\n\n| 方案 | 好处 |\n| --- | --- |\n| 文件 | 简单 |"),
            "reply": node("reply", "question", "建议采用文件。\n\n```html\n<script>bad()</script>\n```", "assistant"),
            "other": node("other", "question", "这是旧分支独有词"),
            "thought": node("thought", "reply", "分析独有词", "assistant", "thoughts"),
        }}
        archive.dump(self.source / "conversations-000.json", [self.conversation])
        self.out = self.root / "out"
        archive.build(argparse.Namespace(source=str(self.source), out=str(self.out), page_messages=2, page_chars=1000))

    def tearDown(self):
        archive.HOME = self.original_home
        target = self.root.resolve()
        allowed = (SCRIPT.parent / "tests" / ".runs").resolve()
        assert target.is_relative_to(allowed) and target != allowed
        shutil.rmtree(target)

    def test_every_message_preserved_and_offsets_are_exact(self):
        manifest = archive.find_conversation(self.out, self.conversation["id"])
        self.assertEqual(len(manifest["messages"]), 4)
        for message in manifest["messages"]:
            original = self.conversation["mapping"][message["node_id"]]["message"]["content"]
            self.assertEqual(archive.message_text(self.out, message), archive.extract_text(original))
            page, anchor = message["html"].split("#")
            self.assertIn('id="' + anchor + '"', (self.out / page).read_text(encoding="utf-8"))
        self.assertEqual(manifest["alternate_count"], 2)

    def test_search_roles_branch_paging_and_literal_chinese(self):
        result = archive.search(self.out, "向量数据库", limit=1)
        self.assertEqual(result["results"][0]["message_id"], "question")
        self.assertEqual(archive.search(self.out, "旧分支独有词")["results"], [])
        self.assertEqual(len(archive.search(self.out, "旧分支独有词", branch="all")["results"]), 1)
        self.assertEqual(archive.search(self.out, "建议")["results"], [])
        self.assertEqual(len(archive.search(self.out, "建议", role="all")["results"]), 1)
        self.assertEqual(archive.search(self.out, "向量数据库", cursor=result["next_cursor"])["results"], [])
        self.assertEqual(len(archive.search(self.out, "分析独有词", role="all", branch="all")["results"]), 1)

    def test_context_uses_real_parents_for_other_branch(self):
        result = archive.read_messages(self.out, self.conversation["id"], "other", 3, 0, 10, 10000)
        self.assertEqual([m["id"] for m in result["messages"]], ["question", "other"])
        clipped = archive.read_messages(self.out, self.conversation["id"], "question", 0, 0, 10, 5)
        self.assertTrue(clipped["truncated"])
        self.assertTrue(clipped["messages"][0]["text_truncated"])

    def test_safe_html_and_table(self):
        manifest = archive.find_conversation(self.out, self.conversation["id"])
        body = (self.out / manifest["messages"][0]["html"].split("#")[0]).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertNotIn("<script>bad()</script>", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertIn("<table>", body)
        self.assertNotIn('<a ', archive.inline('[bad](javascript:alert)'))
        self.assertNotIn('<img ', archive.inline('![remote](https://example.com/a.png)'))
        with self.assertRaises(ValueError):
            archive.inside(self.out, "../outside")

    def test_no_overwrite_and_report(self):
        with self.assertRaises(ValueError):
            archive.build(argparse.Namespace(source=str(self.source), out=str(self.out), page_messages=2, page_chars=1000))
        report = archive.load(self.out / "build-report.json")
        self.assertTrue(report["complete"])
        self.assertEqual(report["messages"], 4)
        self.assertEqual(len(report["sources"][0]["sha256"]), 64)
        self.assertFalse((self.out / "build-in-progress.json").exists())

    def test_multimodal_excerpt_and_both_asset_pointer_formats(self):
        message = {"content_type":"multimodal_text", "parts":[{"content_type":"image_asset_pointer", "asset_pointer":"sediment://file_123"},"这是我真正的问题"]}
        normalized = {"source_content":message,"text":archive.extract_text(message)}
        self.assertEqual(archive.user_excerpt(normalized),"这是我真正的问题")
        self.assertIn("<details>",archive.render_message(normalized))
        self.assertEqual(list(archive.pointers(message)),["file_123"])
        self.assertEqual(list(archive.pointers({"asset_pointer":"file-service://file-abc"})),["file-abc"])
        self.assertEqual(list(archive.pointers({"id":"file-abc","name":"x"})),["file-abc"])

    def test_missing_current_node_is_flagged_and_no_text_lost(self):
        c = dict(self.conversation,current_node="not-present")
        cid,messages,fallback=archive.normalize(c)
        self.assertTrue(fallback)
        self.assertEqual(len(messages),4)


    def test_original_project_ids_names_and_real_last_message_sort(self):
        first = json.loads(json.dumps(self.conversation))
        first["conversation_template_id"] = "g-p-original"
        first["update_time"] = 1999999999
        meta = archive.conversation_metadata(first, {"g-p-original": "原项目名"})
        self.assertEqual(meta["project_id"], "g-p-original")
        self.assertEqual(meta["project_name"], "原项目名")
        self.assertEqual(meta["last_chat_timestamp"], 1729000000)
        second = {**meta, "id": "newer", "created": "2020-01-01", "message_count": 2, "last_chat_timestamp": 1729000100, "project_id": "g-p-different"}
        original = {**meta, "id": "older", "created": "2030-01-01", "message_count": 3}
        ordered = sorted([original, second], key=archive.conversation_sort, reverse=True)
        self.assertEqual(ordered[0]["id"], "newer")
        groups = archive.project_groups(ordered)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["id"], "g-p-different")
        self.assertEqual(archive.conversation_metadata({**first, "conversation_template_id": None}, {})["project_id"], archive.UNASSIGNED)
        self.assertEqual(archive.conversation_metadata({**first, "conversation_template_id": "g-example"}, {})["project_id"], archive.CUSTOM_GPT)

    def test_project_search_filters_user_assistant_and_titles(self):
        items = []
        for pid in ("g-p-one", "g-p-two"):
            c = {**self.conversation, "id": pid + "-conversation", "conversation_template_id": pid}
            args = argparse.Namespace(page_messages=2, page_chars=1000, _project_names={pid: "原项目"})
            items.append(archive.write_conversation(c, "fixture.json", self.out, {}, args))
        archive.write_catalog(self.out, items)
        archive.build_user_index(self.out, items)
        for role, query, titles in (("user", "向量数据库", False), ("all", "建议", False), ("user", "测试", True)):
            result = archive.search(self.out, query, role=role, project_id="g-p-one", title_only=titles)
            self.assertEqual(len(result["results"]), 1)
            self.assertEqual(result["results"][0]["project_id"], "g-p-one")
        self.assertEqual(archive.search(self.out, "向量数据库", project_id="g-p-missing")["results"], [])

    def test_long_conversation_overview_is_paginated(self):
        c = {"id": "many-pages", "title": "很长的会话", "create_time": 1729000000, "current_node": "26", "mapping": {}}
        for i in range(27):
            c["mapping"][str(i)] = {"parent": str(i-1) if i else None, "message": {"id": str(i), "author": {"role": "user"}, "create_time": 1729000000+i, "content": {"content_type": "text", "parts": ["分页原文 " + str(i)]}}}
        item = archive.write_conversation(c, "fixture.json", self.out, {}, argparse.Namespace(page_messages=1, page_chars=1000))
        folder = self.out / Path(item["manifest"]).parent
        self.assertEqual(item["overview_pages"], 3)
        self.assertEqual((folder/"overview.html").read_text(encoding="utf-8").count('<section class="card">'), 12)
        self.assertEqual((folder/"overview-0003.html").read_text(encoding="utf-8").count('<section class="card">'), 3)
        self.assertIn('href="overview-0002.html"', (folder/"overview.html").read_text(encoding="utf-8"))


class ConversationFlowTests(unittest.TestCase):
    def test_one_process_group_with_all_anchors_and_continuous_reply(self):
        def m(key, parent, role="assistant", kind="text", text="正文", branch="main"):
            return dict(id=key, node_id=key, parent_node=parent, anchor="m-"+key, role=role,
                        kind=kind, hidden=False, text=text, asset_ids=[], time="2026-10-20", branch=branch)
        messages = [m("u", None, "user"), m("empty", "u", kind="thoughts", text=""),
                    m("a", "empty"), m("thought", "a", kind="thoughts", text="思考实文"),
                    m("search", "thought", kind="thoughts", text="Searched 4 websites"),
                    m("time", "search", kind="reasoning_recap", text="Worked for 51s"), m("final", "time")]
        content = archive.render_stream(messages, lambda item: '<div class="body">' + archive.markdown(item["text"]) + '</div>')
        self.assertEqual(content.count('class="assistant-turn"'), 1)
        self.assertEqual(content.count('class="process-group"'), 1)
        self.assertEqual(content.count('<strong>ChatGPT</strong>'), 1)
        self.assertEqual(content.count('class="message assistant"'), 2)
        self.assertIn('空记录', content)
        for item in messages:
            self.assertEqual(content.count('id="'+item["anchor"]+'"'), 1)
            if item["text"]: self.assertIn(item["text"], content)

    def test_do_not_merge_distinct_turns_or_alternate_siblings(self):
        messages = [dict(id=key,node_id=key,parent_node=parent,anchor=key,role=role,kind="text",
                         hidden=False,text="内容",asset_ids=[],time="时间",branch=branch)
                    for key,parent,role,branch in [("u",None,"user","main"),("a","u","assistant","main"),
                         ("u2","a","user","main"),("a2","u2","assistant","main"),
                         ("alt1","u2","assistant","alternate"),("alt2","u2","assistant","alternate")]]
        content=archive.render_stream(messages,lambda m: m["text"])
        self.assertEqual(content.count('class="assistant-turn"'),4)
        self.assertEqual(content.count('class="message user"'),2)


class NavigationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Navigation checks optionally use Node.js")
    def test_navigation_state_across_page_reloads(self):
        script = SCRIPT.parent / "tests" / "test_navigation.js"
        result = subprocess.run(["node", str(script)], input=json.dumps({"index": archive.INDEX_JS, "page": archive.PAGE_JS}), text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout)


if __name__ == "__main__":
    unittest.main()
