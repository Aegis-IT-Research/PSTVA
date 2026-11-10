import unittest
from unittest.mock import patch

from modules.tools.horusec.scripts.horusec_scan import horusec_scan_service
from modules.tools.horusec.models.horusec_scan import HorusecScanDTO
from core.app.docker_runner import DockerResult


class TestHorusecScanService(unittest.TestCase):

    @patch("modules.tools.horusec.scripts.horusec_scan.DockerManager")
    @patch("modules.tools.horusec.scripts.horusec_scan.Neo4jManager")
    @patch("modules.tools.horusec.scripts.horusec_scan.prepare_workspace")
    def test_horusec_scan_service_success(
        self, mock_prepare_workspace, mock_neo4j, mock_docker_mgr
    ):
        # Mock workspace preparation
        mock_prepare_workspace.return_value = "/tmp/curium/horusec/test-project"

        # Neo4j mock
        neo = mock_neo4j.return_value
        neo.check_project_exists.return_value = True

        # Fake docker result
        fake_result = DockerResult(
            logs='{"status":"success","analysisVulnerabilities":[]}',
            start_time="2025-01-01T00:00:00",
            end_time="2025-01-01T00:00:10",
            image="curium/horusec:latest",
            command=["horusec", "start"],
        )

        docker = mock_docker_mgr.return_value
        docker.run_container.return_value = fake_result

        payload = HorusecScanDTO(
            project_id="test-project",
            source="/tmp/fake.zip",
        )

        result = horusec_scan_service(payload, "test-project")

        self.assertEqual(result, fake_result)
        neo.check_project_exists.assert_called_once_with("test-project")
        docker.run_container.assert_called_once()
