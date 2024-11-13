import unittest
from unittest.mock import patch, MagicMock, mock_open
from visualizer1 import (
    load_config_from_xml,
    get_commit_data,
    visualize_graph,
    build_plantuml_graph,
)
from datetime import datetime

class TestGitVisualizer(unittest.TestCase):

    @patch("xml.etree.ElementTree.parse")
    def test_load_config_from_xml(self, mock_parse):
        mock_root = MagicMock()
        mock_root.find.return_value.text = "/repo/path"
        mock_root.find.return_value.text = "tool.jar"
        mock_root.find.return_value.text = "/output/path"
        mock_parse.return_value.getroot.return_value = mock_root
        
        config = {
            "visualization_tool": "tool.jar",
            "repository_path": "/repo/path",
            "output_image_path": "/output/path",
            "commit_dates": "2023-11-05 14:32:10",
            "tag_names": ["v1.0"],
        }
        
        self.assertEqual(config["visualization_tool"], "tool.jar")
        self.assertEqual(config["repository_path"], "/repo/path")
        self.assertEqual(config["output_image_path"], "/output/path")
        self.assertEqual(config["commit_dates"], "2023-11-05 14:32:10")
        self.assertEqual(config["tag_names"], ["v1.0"])

    @patch("visualizer1.read_git_object")
    def test_get_commit_data(self, mock_read_git_object):
        commit_content = "author John Doe 1636123800\n\nInitial commit"
        mock_read_git_object.return_value = commit_content
        
        commit_hash = "123abc"
        repo_path = "/repo/path"
        
        commit_data = (
            commit_hash,
            "2021-11-06 05:30:00",
            "John Doe",
            "Initial commit",
        )
        
        self.assertEqual(commit_data[0], commit_hash)
        self.assertEqual(commit_data[1], "2021-11-06 05:30:00")
        self.assertEqual(commit_data[2], "John Doe")
        self.assertEqual(commit_data[3], "Initial commit")

    def test_build_plantuml_graph(self):
        commits_per_tag = {
            "v1.0": [
                ("123abc", "2021-11-06 05:30:00", "John Doe", "Initial commit"),
                ("456def", "2021-11-06 06:00:00", "Jane Doe", "Second commit")
            ]
        }
        
        plantuml_code = build_plantuml_graph(commits_per_tag)
        
        self.assertIn('node "Initial commit\\n2021-11-06 05:30:00\\nJohn Doe" as v1.0_0', plantuml_code)
        self.assertIn('node "Second commit\\n2021-11-06 06:00:00\\nJane Doe" as v1.0_1', plantuml_code)
    @patch("os.system")
    def test_visualize_graph_error(self, mock_system):
        mock_system.return_value = 1 

        with self.assertRaises(Exception):
            visualize_graph('@startuml\nnode "commit" as 1\n@enduml', "tool.jar", "/output/path")


if __name__ == "__main__":
    unittest.main()
