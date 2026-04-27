import sys
import os
import tempfile
import shutil
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evolution.knowledge_graph import KnowledgeGraph, get_knowledge_graph_insight


class TestKnowledgeGraph:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_kg_")
        os.makedirs(os.path.join(self.tmpdir, "evolution"), exist_ok=True)
        self.kg = KnowledgeGraph(self.tmpdir)

    def _teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extract_entities_company(self):
        text = "英伟达发布了新的AI芯片，与AMD展开竞争。"
        entities = self.kg.extract_entities(text)
        assert "company" in entities
        assert "英伟达" in entities["company"]
        assert "AMD" in entities["company"]
        return True

    def test_extract_entities_technology(self):
        text = "GPT-4和深度学习技术正在改变AI行业。"
        entities = self.kg.extract_entities(text)
        assert "technology" in entities
        assert "AI" in entities["technology"]
        assert "深度学习" in entities["technology"]
        return True

    def test_extract_entities_multiple_types(self):
        text = "OpenAI的ChatGPT使用大模型技术，马斯克表示关注。"
        entities = self.kg.extract_entities(text)
        assert "company" in entities and "OpenAI" in entities["company"]
        assert "product" in entities and "ChatGPT" in entities["product"]
        assert "technology" in entities and "大模型" in entities["technology"]
        assert "person" in entities and "马斯克" in entities["person"]
        return True

    def test_extract_entities_empty(self):
        entities = self.kg.extract_entities("这是一篇没有任何技术内容的文章。")
        assert len(entities) == 0 or all(len(v) == 0 for v in entities.values())
        return True

    def test_find_relations_compete(self):
        text = "英伟达和AMD在GPU市场展开激烈竞争。"
        entities = self.kg.extract_entities(text)
        relations = self.kg.find_relations(text, entities)
        assert len(relations) > 0
        assert any(r["relation"] == "compete" for r in relations)
        return True

    def test_find_relations_cooperate(self):
        text = "苹果和台积电合作生产芯片。"
        entities = self.kg.extract_entities(text)
        relations = self.kg.find_relations(text, entities)
        assert any(r["relation"] == "cooperate" for r in relations)
        return True

    def test_build_graph_structure(self):
        text = "英伟达发布H100，AMD推出MI300X与之竞争。"
        graph = self.kg.build_graph_from_content(text)
        assert "entities" in graph
        assert "relations" in graph
        assert graph["entity_count"] > 0
        assert "relation_count" in graph
        return True

    def test_generate_insight_with_entities(self):
        text = "英伟达和AMD竞争AI芯片市场。"
        graph = self.kg.build_graph_from_content(text)
        insight = self.kg.generate_graph_insight(graph)
        assert len(insight) > 0
        assert "英伟达" in insight or "AMD" in insight
        return True

    def test_generate_insight_empty(self):
        graph = {"entities": {}, "relations": [], "entity_count": 0, "relation_count": 0}
        insight = self.kg.generate_graph_insight(graph)
        assert insight == ""
        return True

    def test_save_and_load_graph(self):
        graph = {
            "entities": {"company": ["英伟达"]},
            "relations": [],
            "entity_count": 1,
            "relation_count": 0
        }
        self.kg.save_graph("2024-01-01", graph)
        assert os.path.exists(self.kg.graph_file)
        with open(self.kg.graph_file, 'r') as f:
            data = json.load(f)
        assert "2024-01-01" in data
        return True

    def test_get_entity_history(self):
        graph = {
            "entities": {"company": ["英伟达"]},
            "relations": [],
            "entity_count": 1,
            "relation_count": 0
        }
        self.kg.save_graph("2024-01-01", graph)
        history = self.kg.get_entity_history("英伟达")
        assert len(history) > 0
        assert history[0]["date"] == "2024-01-01"
        return True

    def test_get_knowledge_graph_insight(self):
        result = get_knowledge_graph_insight("英伟达发布新芯片。", self.tmpdir)
        assert isinstance(result, str)
        return True

    def run_all(self):
        tests = [
            self.test_extract_entities_company,
            self.test_extract_entities_technology,
            self.test_extract_entities_multiple_types,
            self.test_extract_entities_empty,
            self.test_find_relations_compete,
            self.test_find_relations_cooperate,
            self.test_build_graph_structure,
            self.test_generate_insight_with_entities,
            self.test_generate_insight_empty,
            self.test_save_and_load_graph,
            self.test_get_entity_history,
            self.test_get_knowledge_graph_insight,
        ]
        passed = 0
        failed = []
        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                failed.append((test.__name__, str(e)))
        self._teardown()
        return {"passed": passed, "failed": failed, "total": len(tests)}
