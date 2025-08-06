"""Tests for the JenkinsApi class."""

import pytest
from unittest.mock import patch
import jenkins

from mcp_server.libs.jenkins_api import (
    JenkinsApi,
    JenkinsApiError,
    JenkinsConnectionError,
    JenkinsJobNotFoundError,
)


class TestJenkinsApiInit:
    """Test JenkinsApi initialization."""

    def test_init_with_valid_env_vars(self, mock_env_vars, mock_logger):
        """Test successful initialization with valid environment variables."""
        with patch("jenkins.Jenkins.__init__", return_value=None) as mock_jenkins_init:
            api = JenkinsApi()

            # Verify Jenkins parent constructor was called with correct parameters
            mock_jenkins_init.assert_called_once_with(
                url="http://test-jenkins.com",
                username="test_user",
                password="test_password",  # pragma: allowlist secret
            )

            # Verify logger was configured
            assert api.logger is not None
            mock_logger.info.assert_called_once_with("Connecting to Jenkins server: http://test-jenkins.com")

    def test_init_missing_jenkins_url(self, monkeypatch, mock_logger):
        """Test initialization fails when JENKINS_URL is missing."""
        monkeypatch.setenv("JENKINS_USERNAME", "test_user")
        monkeypatch.setenv("JENKINS_PASSWORD", "test_password")
        monkeypatch.delenv("JENKINS_URL", raising=False)

        with pytest.raises(ValueError) as exc_info:
            JenkinsApi()

        assert "Missing Jenkins credentials" in str(exc_info.value)
        assert "JENKINS_URL" in str(exc_info.value)

    def test_init_missing_jenkins_username(self, monkeypatch, mock_logger):
        """Test initialization fails when JENKINS_USERNAME is missing."""
        monkeypatch.setenv("JENKINS_URL", "http://test-jenkins.com")
        monkeypatch.setenv("JENKINS_PASSWORD", "test_password")
        monkeypatch.delenv("JENKINS_USERNAME", raising=False)

        with pytest.raises(ValueError) as exc_info:
            JenkinsApi()

        assert "Missing Jenkins credentials" in str(exc_info.value)
        assert "JENKINS_USERNAME" in str(exc_info.value)

    def test_init_missing_jenkins_password(self, monkeypatch, mock_logger):
        """Test initialization fails when JENKINS_PASSWORD is missing."""
        monkeypatch.setenv("JENKINS_URL", "http://test-jenkins.com")
        monkeypatch.setenv("JENKINS_USERNAME", "test_user")
        monkeypatch.delenv("JENKINS_PASSWORD", raising=False)

        with pytest.raises(ValueError) as exc_info:
            JenkinsApi()

        assert "Missing Jenkins credentials" in str(exc_info.value)
        assert "JENKINS_PASSWORD" in str(exc_info.value)

    def test_init_missing_all_env_vars(self, missing_env_vars, mock_logger):
        """Test initialization fails when all environment variables are missing."""
        with pytest.raises(ValueError) as exc_info:
            JenkinsApi()

        error_message = str(exc_info.value)
        assert "Missing Jenkins credentials" in error_message
        assert "JENKINS_URL" in error_message
        assert "JENKINS_USERNAME" in error_message
        assert "JENKINS_PASSWORD" in error_message

    def test_init_sets_https_verify_env(self, mock_env_vars, mock_logger):
        """Test that initialization sets PYTHONHTTPSVERIFY environment variable."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            with patch("os.environ") as mock_environ:
                JenkinsApi()
                mock_environ.__setitem__.assert_any_call("PYTHONHTTPSVERIFY", "0")


class TestJenkinsApiGetJobDetails:
    """Test get_job_details method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    def test_get_job_details_success(self, jenkins_api, sample_job_info, mock_logger):
        """Test successful job details retrieval."""
        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            result = jenkins_api.get_job_details("test-job")

            assert result == sample_job_info
            mock_logger.info.assert_any_call("Getting job info for: test-job")
            mock_logger.info.assert_any_call("Successfully retrieved job info for: test-job")

    def test_get_job_details_jenkins_exception(self, jenkins_api, jenkins_exception, mock_logger):
        """Test handling of Jenkins exception."""
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_exception):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_job_details("test-job")

            assert "Jenkins error getting job info for 'test-job'" in str(exc_info.value)
            assert "Jenkins server error" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_get_job_details_generic_exception(self, jenkins_api, mock_logger):
        """Test handling of generic exception."""
        with patch.object(jenkins_api, "get_job_info", side_effect=Exception("Network error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_job_details("test-job")

            assert "Unexpected error getting job info for 'test-job'" in str(exc_info.value)
            assert "Network error" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_get_job_details_nonexistent_job(self, jenkins_api, mock_logger):
        """Test retrieving details for non-existent job."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.get_job_details("nonexistent-job")

            assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)

    def test_get_job_details_connection_error(self, jenkins_api, mock_logger):
        """Test handling of connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.get_job_details("test-job")

            assert "Connection error while getting job 'test-job'" in str(exc_info.value)
            assert "Connection timeout" in str(exc_info.value)


class TestJenkinsApiRunJob:
    """Test run_job method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    def test_run_job_without_parameters(self, jenkins_api, sample_job_info, mock_logger):
        """Test running job without parameters."""
        with patch.object(jenkins_api, "build_job") as mock_build_job:
            with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
                result = jenkins_api.run_job("test-job")

                mock_build_job.assert_called_once_with("test-job")
                assert "Job 'test-job' started successfully. Build number: 2" in result
                mock_logger.info.assert_any_call("Running job: test-job with parameters: None")

    def test_run_job_with_parameters(self, jenkins_api, sample_job_info, valid_job_parameters, mock_logger):
        """Test running job with parameters."""
        with patch.object(jenkins_api, "build_job") as mock_build_job:
            with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
                result = jenkins_api.run_job("test-job", valid_job_parameters)

                mock_build_job.assert_called_once_with("test-job", valid_job_parameters)
                assert "Job 'test-job' started successfully. Build number: 2" in result
                mock_logger.info.assert_any_call(f"Running job: test-job with parameters: {valid_job_parameters}")

    def test_run_job_jenkins_exception(self, jenkins_api, jenkins_exception, mock_logger):
        """Test handling of Jenkins exception during job run."""
        with patch.object(jenkins_api, "build_job", side_effect=jenkins_exception):
            result = jenkins_api.run_job("test-job")

            assert isinstance(result, str)
            assert "Jenkins error running job 'test-job'" in result
            assert "Jenkins server error" in result
            mock_logger.error.assert_called_once()

    def test_run_job_generic_exception(self, jenkins_api, mock_logger):
        """Test handling of generic exception during job run."""
        with patch.object(jenkins_api, "build_job", side_effect=Exception("Build failed")):
            result = jenkins_api.run_job("test-job")

            assert isinstance(result, str)
            assert "Unexpected error running job 'test-job'" in result
            assert "Build failed" in result
            mock_logger.error.assert_called_once()

    def test_run_job_build_number_calculation(self, jenkins_api, mock_logger):
        """Test that build number is calculated correctly."""
        job_info = {"nextBuildNumber": 5}
        with patch.object(jenkins_api, "build_job"):
            with patch.object(jenkins_api, "get_job_info", return_value=job_info):
                result = jenkins_api.run_job("test-job")

                assert "Build number: 4" in result

    def test_run_job_disabled_job(self, jenkins_api, mock_logger):
        """Test running a disabled job."""
        jenkins_error = jenkins.JenkinsException("job[test-job] is disabled")
        with patch.object(jenkins_api, "build_job", side_effect=jenkins_error):
            result = jenkins_api.run_job("test-job")

            assert isinstance(result, str)
            assert "Jenkins error running job 'test-job'" in result
            assert "is disabled" in result


class TestJenkinsApiGetJobConsole:
    """Test get_job_console method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    def test_get_job_console_with_build_number(self, jenkins_api, sample_console_output, mock_logger):
        """Test getting console output with specific build number."""
        with patch.object(jenkins_api, "get_build_console_output", return_value=sample_console_output):
            result = jenkins_api.get_job_console("test-job", 2)

            assert result == sample_console_output
            mock_logger.info.assert_any_call("Getting console output for job: test-job, build: 2")
            mock_logger.info.assert_any_call("Successfully retrieved console output for: test-job#2")

    def test_get_job_console_without_build_number(
        self, jenkins_api, sample_job_info, sample_console_output, mock_logger
    ):
        """Test getting console output without build number (uses latest)."""
        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            with patch.object(jenkins_api, "get_build_console_output", return_value=sample_console_output):
                result = jenkins_api.get_job_console("test-job")

                assert result == sample_console_output
                mock_logger.info.assert_any_call("Getting console output for job: test-job, build: 2")

    def test_get_job_console_no_builds_available(self, jenkins_api, empty_job_info, mock_logger):
        """Test getting console output when no builds are available."""
        with patch.object(jenkins_api, "get_job_info", return_value=empty_job_info):
            result = jenkins_api.get_job_console("test-job")

            assert isinstance(result, str)
            assert "No builds found for job 'test-job'" in result
            mock_logger.error.assert_called_once()

    def test_get_job_console_jenkins_exception(self, jenkins_api, jenkins_exception, mock_logger):
        """Test handling of Jenkins exception during console output retrieval."""
        with patch.object(jenkins_api, "get_build_console_output", side_effect=jenkins_exception):
            result = jenkins_api.get_job_console("test-job", 1)

            assert isinstance(result, str)
            assert "Jenkins error getting console output for 'test-job#1'" in result
            assert "Jenkins server error" in result
            mock_logger.error.assert_called_once()

    def test_get_job_console_generic_exception(self, jenkins_api, mock_logger):
        """Test handling of generic exception during console output retrieval."""
        with patch.object(jenkins_api, "get_build_console_output", side_effect=Exception("Connection timeout")):
            result = jenkins_api.get_job_console("test-job", 1)

            assert isinstance(result, str)
            assert "Unexpected error getting console output for 'test-job#1'" in result
            assert "Connection timeout" in result
            mock_logger.error.assert_called_once()

    def test_get_job_console_build_not_found(self, jenkins_api, mock_logger):
        """Test getting console output for non-existent build."""
        jenkins_error = jenkins.JenkinsException("build[999] does not exist")
        with patch.object(jenkins_api, "get_build_console_output", side_effect=jenkins_error):
            result = jenkins_api.get_job_console("test-job", 999)

            assert isinstance(result, str)
            assert "Jenkins error getting console output for 'test-job#999'" in result
            assert "does not exist" in result

    def test_get_job_console_none_build_number_edge_case(
        self, jenkins_api, sample_job_info, sample_console_output, mock_logger
    ):
        """Test the assertion logic when build_number becomes None through an edge case."""
        # Create a job info with lastBuild but modify it to simulate edge case
        modified_job_info = sample_job_info.copy()
        modified_job_info["lastBuild"] = None

        with patch.object(jenkins_api, "get_job_info", return_value=modified_job_info):
            result = jenkins_api.get_job_console("test-job", None)

            assert isinstance(result, str)
            assert "No builds found for job 'test-job'" in result


class TestJenkinsApiGetAllJobsList:
    """Test get_all_jobs_list method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    def test_get_all_jobs_list_success(self, jenkins_api, sample_jobs_list, mock_logger):
        """Test successful retrieval of all jobs list."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=sample_jobs_list):
            result = jenkins_api.get_all_jobs_list()

            assert result == sample_jobs_list
            mock_logger.info.assert_any_call("Getting list of all jobs")
            mock_logger.info.assert_any_call("Successfully retrieved 3 jobs")

    def test_get_all_jobs_list_empty(self, jenkins_api, mock_logger):
        """Test retrieval of empty jobs list."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=[]):
            result = jenkins_api.get_all_jobs_list()

            assert result == []
            mock_logger.info.assert_any_call("Successfully retrieved 0 jobs")

    def test_get_all_jobs_list_jenkins_exception(self, jenkins_api, jenkins_exception, mock_logger):
        """Test handling of Jenkins exception during jobs list retrieval."""
        with patch.object(jenkins_api, "get_all_jobs", side_effect=jenkins_exception):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_all_jobs_list()

            assert "Jenkins error getting jobs list" in str(exc_info.value)
            assert "Jenkins server error" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_get_all_jobs_list_generic_exception(self, jenkins_api, mock_logger):
        """Test handling of generic exception during jobs list retrieval."""
        with patch.object(jenkins_api, "get_all_jobs", side_effect=Exception("Server unreachable")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_all_jobs_list()

            assert "Unexpected error getting jobs list" in str(exc_info.value)
            assert "Server unreachable" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_get_all_jobs_list_permission_error(self, jenkins_api, mock_logger):
        """Test handling of permission error during jobs list retrieval."""
        jenkins_error = jenkins.JenkinsException("User 'test_user' is missing the Overall/Read permission")
        with patch.object(jenkins_api, "get_all_jobs", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_all_jobs_list()

            assert "Permission error getting jobs list" in str(exc_info.value)
            assert "missing the Overall/Read permission" in str(exc_info.value)

    def test_get_all_jobs_list_connection_error(self, jenkins_api, mock_logger):
        """Test handling of connection error during jobs list retrieval."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_all_jobs", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.get_all_jobs_list()

            assert "Connection error while getting jobs list" in str(exc_info.value)
            assert "Connection timeout" in str(exc_info.value)


class TestJenkinsApiEdgeCases:
    """Test edge cases and complex scenarios."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    def test_concurrent_api_calls(self, jenkins_api, sample_job_info, mock_logger):
        """Test that the API can handle multiple concurrent calls."""
        import concurrent.futures

        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(jenkins_api.get_job_details, f"job-{i}") for i in range(3)]

                results = [future.result() for future in concurrent.futures.as_completed(futures)]

                # All results should be successful
                assert all(isinstance(result, dict) for result in results)
                assert all(result["name"] == "test-job" for result in results)

    def test_very_long_job_name(self, jenkins_api, mock_logger):
        """Test handling of very long job names."""
        long_job_name = "a" * 1000  # Very long job name
        jenkins_error = jenkins.JenkinsException("Job name too long")

        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_job_details(long_job_name)

            assert "Jenkins error getting job info" in str(exc_info.value)

    def test_special_characters_in_job_name(self, jenkins_api, sample_job_info, mock_logger):
        """Test handling of special characters in job names."""
        special_job_name = "test-job/with spaces & symbols!@#$%"

        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            result = jenkins_api.get_job_details(special_job_name)

            assert result == sample_job_info

    def test_unicode_job_name(self, jenkins_api, sample_job_info, mock_logger):
        """Test handling of unicode characters in job names."""
        unicode_job_name = "test-job-ñáéíóú-🚀"

        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            result = jenkins_api.get_job_details(unicode_job_name)

            assert result == sample_job_info

    def test_large_console_output(self, jenkins_api, mock_logger):
        """Test handling of very large console output."""
        large_console_output = "Console line\n" * 10000  # Large output

        with patch.object(jenkins_api, "get_build_console_output", return_value=large_console_output):
            result = jenkins_api.get_job_console("test-job", 1)

            assert result == large_console_output
            assert len(result) > 100000  # Verify it's actually large

    def test_network_timeout_simulation(self, jenkins_api, mock_logger):
        """Test handling of network timeout scenarios."""
        timeout_error = Exception("HTTPSConnectionPool timeout")

        with patch.object(jenkins_api, "get_job_info", side_effect=timeout_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_job_details("test-job")

            assert "Unexpected error getting job info" in str(exc_info.value)
            assert "timeout" in str(exc_info.value)
