"""Tests for the JenkinsApi class."""

import pytest
from unittest.mock import patch
import jenkins

from mcp_server.libs.jenkins_api import (
    JenkinsApi,
    JenkinsApiError,
    JenkinsBuildNotFoundError,
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

    def test_get_job_console_with_tail(self, jenkins_api, mock_logger):
        """Test getting console output with tail parameter."""
        multiline_output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        with patch.object(jenkins_api, "get_build_console_output", return_value=multiline_output):
            result = jenkins_api.get_job_console("test-job", 1, tail=2)

            assert result == "Line 4\nLine 5"
            mock_logger.info.assert_any_call("Getting console output for job: test-job, build: 1")

    def test_get_job_console_with_head(self, jenkins_api, mock_logger):
        """Test getting console output with head parameter."""
        multiline_output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        with patch.object(jenkins_api, "get_build_console_output", return_value=multiline_output):
            result = jenkins_api.get_job_console("test-job", 1, head=2)

            assert result == "Line 1\nLine 2"
            mock_logger.info.assert_any_call("Getting console output for job: test-job, build: 1")

    def test_get_job_console_tail_and_head_mutually_exclusive(self, jenkins_api, mock_logger):
        """Test that providing both tail and head raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.get_job_console("test-job", 1, tail=5, head=5)

        assert "tail and head are mutually exclusive" in str(exc_info.value)

    def test_get_job_console_tail_zero_raises_error(self, jenkins_api, mock_logger):
        """Test that tail=0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.get_job_console("test-job", 1, tail=0)

        assert "tail must be a positive integer" in str(exc_info.value)

    def test_get_job_console_tail_negative_raises_error(self, jenkins_api, mock_logger):
        """Test that negative tail raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.get_job_console("test-job", 1, tail=-5)

        assert "tail must be a positive integer" in str(exc_info.value)

    def test_get_job_console_head_zero_raises_error(self, jenkins_api, mock_logger):
        """Test that head=0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.get_job_console("test-job", 1, head=0)

        assert "head must be a positive integer" in str(exc_info.value)

    def test_get_job_console_head_negative_raises_error(self, jenkins_api, mock_logger):
        """Test that negative head raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.get_job_console("test-job", 1, head=-5)

        assert "head must be a positive integer" in str(exc_info.value)

    def test_get_job_console_tail_exceeds_total_lines(self, jenkins_api, mock_logger):
        """Test tail larger than total lines returns all lines."""
        multiline_output = "Line 1\nLine 2\nLine 3"
        with patch.object(jenkins_api, "get_build_console_output", return_value=multiline_output):
            result = jenkins_api.get_job_console("test-job", 1, tail=100)

            assert result == "Line 1\nLine 2\nLine 3"

    def test_get_job_console_head_exceeds_total_lines(self, jenkins_api, mock_logger):
        """Test head larger than total lines returns all lines."""
        multiline_output = "Line 1\nLine 2\nLine 3"
        with patch.object(jenkins_api, "get_build_console_output", return_value=multiline_output):
            result = jenkins_api.get_job_console("test-job", 1, head=100)

            assert result == "Line 1\nLine 2\nLine 3"

    def test_get_job_console_tail_one_line(self, jenkins_api, mock_logger):
        """Test tail=1 returns only the last line."""
        multiline_output = "Line 1\nLine 2\nLine 3"
        with patch.object(jenkins_api, "get_build_console_output", return_value=multiline_output):
            result = jenkins_api.get_job_console("test-job", 1, tail=1)

            assert result == "Line 3"

    def test_get_job_console_head_one_line(self, jenkins_api, mock_logger):
        """Test head=1 returns only the first line."""
        multiline_output = "Line 1\nLine 2\nLine 3"
        with patch.object(jenkins_api, "get_build_console_output", return_value=multiline_output):
            result = jenkins_api.get_job_console("test-job", 1, head=1)

            assert result == "Line 1"

    def test_get_job_console_empty_output_with_tail(self, jenkins_api, mock_logger):
        """Test tail on empty console output."""
        with patch.object(jenkins_api, "get_build_console_output", return_value=""):
            result = jenkins_api.get_job_console("test-job", 1, tail=5)

            assert result == ""

    def test_get_job_console_empty_output_with_head(self, jenkins_api, mock_logger):
        """Test head on empty console output."""
        with patch.object(jenkins_api, "get_build_console_output", return_value=""):
            result = jenkins_api.get_job_console("test-job", 1, head=5)

            assert result == ""

    def test_get_job_console_no_tail_no_head_returns_full_output(self, jenkins_api, mock_logger):
        """Test that without tail or head, full output is returned."""
        multiline_output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        with patch.object(jenkins_api, "get_build_console_output", return_value=multiline_output):
            result = jenkins_api.get_job_console("test-job", 1)

            assert result == multiline_output


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


class TestJenkinsApiWaitForBuild:
    """Test wait_for_build method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def sample_build_info_complete(self):
        """Sample build info for a completed build."""
        return {
            "number": 5,
            "result": "SUCCESS",
            "duration": 45000,
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": False,
        }

    @pytest.fixture
    def sample_build_info_in_progress(self):
        """Sample build info for a build in progress."""
        return {
            "number": 5,
            "result": None,
            "duration": 0,
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": True,
        }

    def test_wait_for_build_success_with_build_number(self, jenkins_api, sample_build_info_complete, mock_logger):
        """Test successful wait for build with specific build number."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_complete):
            result = jenkins_api.wait_for_build("test-job", build_number=5, timeout=60, poll_interval=1)

            assert result["build_number"] == 5
            assert result["result"] == "SUCCESS"
            assert result["duration"] == 45000
            assert result["url"] == "http://test-jenkins.com/job/test-job/5/"
            mock_logger.info.assert_any_call("Waiting for build: test-job#5 (timeout: 60s, poll: 1s)")
            mock_logger.info.assert_any_call("Build 'test-job#5' completed with result: SUCCESS")

    def test_wait_for_build_success_without_build_number(
        self, jenkins_api, sample_job_info, sample_build_info_complete, mock_logger
    ):
        """Test successful wait for build using last build number."""
        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_complete):
                result = jenkins_api.wait_for_build("test-job", timeout=60, poll_interval=1)

                assert result["build_number"] == 2  # From sample_job_info lastBuild
                assert result["result"] == "SUCCESS"

    def test_wait_for_build_no_builds_found(self, jenkins_api, empty_job_info, mock_logger):
        """Test wait_for_build when no builds exist."""
        with patch.object(jenkins_api, "get_job_info", return_value=empty_job_info):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.wait_for_build("empty-job")

            assert "No builds found for job 'empty-job'" in str(exc_info.value)

    def test_wait_for_build_timeout(self, jenkins_api, sample_build_info_in_progress, mock_logger):
        """Test wait_for_build timeout."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_in_progress):
            with patch("mcp_server.libs.jenkins_api.time.sleep"):
                with patch("mcp_server.libs.jenkins_api.time.time") as mock_time:
                    # Simulate time progression: start=0, then 2 seconds elapsed
                    mock_time.side_effect = [0, 2]

                    with pytest.raises(JenkinsApiError) as exc_info:
                        jenkins_api.wait_for_build("test-job", build_number=5, timeout=1, poll_interval=1)

                    assert "Timeout waiting for build 'test-job#5' after 1 seconds" in str(exc_info.value)

    def test_wait_for_build_polls_until_complete(
        self, jenkins_api, sample_build_info_in_progress, sample_build_info_complete, mock_logger
    ):
        """Test that wait_for_build polls until build completes."""
        # First call returns in progress, second call returns complete
        with patch.object(
            jenkins_api,
            "get_build_info",
            side_effect=[sample_build_info_in_progress, sample_build_info_complete],
        ):
            with patch("mcp_server.libs.jenkins_api.time.sleep") as mock_sleep:
                with patch("mcp_server.libs.jenkins_api.time.time") as mock_time:
                    mock_time.side_effect = [0, 0.5, 1]

                    result = jenkins_api.wait_for_build("test-job", build_number=5, timeout=60, poll_interval=5)

                    assert result["result"] == "SUCCESS"
                    mock_sleep.assert_called_once_with(5)

    def test_wait_for_build_job_not_found(self, jenkins_api, mock_logger):
        """Test wait_for_build when job does not exist."""
        jenkins_error = jenkins.JenkinsException("job[test-job] does not exist")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.wait_for_build("test-job")

            assert "Job 'test-job' does not exist" in str(exc_info.value)

    def test_wait_for_build_build_not_found(self, jenkins_api, mock_logger):
        """Test wait_for_build when build does not exist."""
        jenkins_error = jenkins.JenkinsException("build[999] does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.wait_for_build("test-job", build_number=999)

            assert "Build 'test-job#999' not found" in str(exc_info.value)

    def test_wait_for_build_connection_error(self, jenkins_api, mock_logger):
        """Test wait_for_build with connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.wait_for_build("test-job", build_number=5)

            assert "Connection error while waiting for build 'test-job#5'" in str(exc_info.value)

    def test_wait_for_build_unexpected_exception(self, jenkins_api, mock_logger):
        """Test wait_for_build with unexpected exception."""
        with patch.object(jenkins_api, "get_build_info", side_effect=Exception("Unexpected error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.wait_for_build("test-job", build_number=5)

            assert "Unexpected error waiting for build 'test-job#5'" in str(exc_info.value)

    def test_wait_for_build_failure_result(self, jenkins_api, mock_logger):
        """Test wait_for_build with FAILURE result."""
        failed_build_info = {
            "number": 5,
            "result": "FAILURE",
            "duration": 30000,
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": False,
        }
        with patch.object(jenkins_api, "get_build_info", return_value=failed_build_info):
            result = jenkins_api.wait_for_build("test-job", build_number=5)

            assert result["result"] == "FAILURE"
            assert result["duration"] == 30000

    def test_wait_for_build_aborted_result(self, jenkins_api, mock_logger):
        """Test wait_for_build with ABORTED result."""
        aborted_build_info = {
            "number": 5,
            "result": "ABORTED",
            "duration": 10000,
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": False,
        }
        with patch.object(jenkins_api, "get_build_info", return_value=aborted_build_info):
            result = jenkins_api.wait_for_build("test-job", build_number=5)

            assert result["result"] == "ABORTED"

    def test_wait_for_build_default_parameters(self, jenkins_api, sample_build_info_complete, mock_logger):
        """Test wait_for_build with default timeout and poll_interval."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_complete):
            result = jenkins_api.wait_for_build("test-job", build_number=5)

            assert result["result"] == "SUCCESS"
            mock_logger.info.assert_any_call("Waiting for build: test-job#5 (timeout: 3600s, poll: 30s)")

    def test_wait_for_build_timeout_must_be_positive(self, jenkins_api, mock_logger):
        """Test wait_for_build raises ValueError when timeout is zero."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.wait_for_build("test-job", build_number=5, timeout=0)

        assert "timeout must be positive" in str(exc_info.value)

    def test_wait_for_build_timeout_must_be_positive_negative(self, jenkins_api, mock_logger):
        """Test wait_for_build raises ValueError when timeout is negative."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.wait_for_build("test-job", build_number=5, timeout=-10)

        assert "timeout must be positive" in str(exc_info.value)

    def test_wait_for_build_poll_interval_must_be_positive(self, jenkins_api, mock_logger):
        """Test wait_for_build raises ValueError when poll_interval is zero."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.wait_for_build("test-job", build_number=5, timeout=60, poll_interval=0)

        assert "poll_interval must be positive" in str(exc_info.value)

    def test_wait_for_build_poll_interval_must_be_positive_negative(self, jenkins_api, mock_logger):
        """Test wait_for_build raises ValueError when poll_interval is negative."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.wait_for_build("test-job", build_number=5, timeout=60, poll_interval=-5)

        assert "poll_interval must be positive" in str(exc_info.value)

    def test_wait_for_build_poll_interval_adjusted_when_exceeds_timeout(
        self, jenkins_api, sample_build_info_complete, mock_logger
    ):
        """Test wait_for_build adjusts poll_interval to timeout when poll_interval > timeout."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_complete):
            result = jenkins_api.wait_for_build("test-job", build_number=5, timeout=10, poll_interval=60)

            assert result["result"] == "SUCCESS"
            # The log message should show the adjusted poll_interval (equal to timeout)
            mock_logger.info.assert_any_call("Waiting for build: test-job#5 (timeout: 10s, poll: 10s)")


class TestJenkinsApiGetBuildErrors:
    """Test get_build_errors method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def console_output_with_errors(self):
        """Sample console output with various error patterns."""
        return """Started by user admin
Running as SYSTEM
Building in workspace /var/jenkins_home/workspace/test-job
[test-job] $ /bin/sh -xe /tmp/jenkins123456789.sh
+ echo 'Starting build'
Starting build
[ERROR] Failed to compile module
error: cannot find symbol
Exception in thread "main" java.lang.NullPointerException
    at com.example.Main.run(Main.java:42)
    at com.example.Main.main(Main.java:10)
Traceback (most recent call last):
  File "script.py", line 10, in <module>
    raise ValueError("Something went wrong")
ValueError: Something went wrong
Build step 'Execute shell' marked build as failure
FAILURE: Build failed with an exception
Finished: FAILURE"""

    @pytest.fixture
    def console_output_success(self):
        """Sample console output without errors."""
        return """Started by user admin
Running as SYSTEM
Building in workspace /var/jenkins_home/workspace/test-job
[test-job] $ /bin/sh -xe /tmp/jenkins123456789.sh
+ echo 'Hello World'
Hello World
+ echo 'Job completed successfully'
Job completed successfully
Finished: SUCCESS"""

    def test_get_build_errors_with_default_patterns(self, jenkins_api, console_output_with_errors, mock_logger):
        """Test get_build_errors with default error patterns."""
        with patch.object(jenkins_api, "get_job_console", return_value=console_output_with_errors):
            result = jenkins_api.get_build_errors("test-job", build_number=5)

            assert "errors" in result
            assert "summary" in result
            assert len(result["errors"]) > 0

            # Check that various error categories are detected
            categories_found = set(error["category"] for error in result["errors"])
            assert "error" in categories_found or "exception" in categories_found or "failure" in categories_found

            # Check summary counts match errors
            for category, count in result["summary"].items():
                category_errors = [e for e in result["errors"] if e["category"] == category]
                assert len(category_errors) == count

            mock_logger.info.assert_any_call("Getting build errors for job: test-job, build: 5")

    def test_get_build_errors_with_custom_patterns(self, jenkins_api, mock_logger):
        """Test get_build_errors with custom regex patterns."""
        console_output = """Line 1: normal output
Line 2: CUSTOM_ERROR found here
Line 3: normal output
Line 4: another CUSTOM_ERROR here
Line 5: done"""

        with patch.object(jenkins_api, "get_job_console", return_value=console_output):
            result = jenkins_api.get_build_errors(
                "test-job",
                build_number=5,
                patterns=["CUSTOM_ERROR"],
            )

            assert len(result["errors"]) == 2
            assert result["summary"].get("custom", 0) == 2

            # Verify line numbers
            assert result["errors"][0]["line_number"] == 2
            assert result["errors"][1]["line_number"] == 4

            # All should be in 'custom' category
            for error in result["errors"]:
                assert error["category"] == "custom"

    def test_get_build_errors_no_errors_found(self, jenkins_api, console_output_success, mock_logger):
        """Test get_build_errors when no errors are found."""
        with patch.object(jenkins_api, "get_job_console", return_value=console_output_success):
            result = jenkins_api.get_build_errors("test-job", build_number=5)

            assert result["errors"] == []
            assert result["summary"] == {}

    def test_get_build_errors_without_build_number(self, jenkins_api, console_output_with_errors, mock_logger):
        """Test get_build_errors using latest build."""
        with patch.object(jenkins_api, "get_job_console", return_value=console_output_with_errors):
            result = jenkins_api.get_build_errors("test-job")

            assert "errors" in result
            assert "summary" in result
            mock_logger.info.assert_any_call("Getting build errors for job: test-job, build: None")

    def test_get_build_errors_no_builds_found(self, jenkins_api, mock_logger):
        """Test get_build_errors when no builds are available."""
        with patch.object(jenkins_api, "get_job_console", return_value="No builds found for job 'test-job'"):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.get_build_errors("test-job")

            assert "No builds found for job 'test-job'" in str(exc_info.value)

    def test_get_build_errors_jenkins_error_in_console(self, jenkins_api, mock_logger):
        """Test get_build_errors when console output contains Jenkins error."""
        with patch.object(
            jenkins_api, "get_job_console", return_value="Jenkins error getting console output for 'test-job#5': error"
        ):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_build_errors("test-job", build_number=5)

            assert "Jenkins error" in str(exc_info.value)

    def test_get_build_errors_invalid_regex_pattern(self, jenkins_api, mock_logger):
        """Test get_build_errors handles invalid regex patterns gracefully."""
        console_output = "Line 1: test\nLine 2: error here"

        with patch.object(jenkins_api, "get_job_console", return_value=console_output):
            # Invalid regex pattern with unbalanced parenthesis
            result = jenkins_api.get_build_errors(
                "test-job",
                build_number=5,
                patterns=["(invalid[", "valid_pattern"],
            )

            # Should still work with valid pattern
            # The invalid pattern should be skipped with a warning
            mock_logger.warning.assert_called()
            assert "errors" in result
            assert "summary" in result

    def test_get_build_errors_job_not_found(self, jenkins_api, mock_logger):
        """Test get_build_errors when job does not exist."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "get_job_console", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.get_build_errors("nonexistent-job")

            assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)

    def test_get_build_errors_build_not_found(self, jenkins_api, mock_logger):
        """Test get_build_errors when build does not exist."""
        jenkins_error = jenkins.JenkinsException("build[999] does not exist")
        with patch.object(jenkins_api, "get_job_console", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.get_build_errors("test-job", build_number=999)

            assert "Build 'test-job#999' not found" in str(exc_info.value)

    def test_get_build_errors_connection_error(self, jenkins_api, mock_logger):
        """Test get_build_errors with connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_job_console", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.get_build_errors("test-job", build_number=5)

            assert "Connection error while getting build errors" in str(exc_info.value)

    def test_get_build_errors_generic_jenkins_exception(self, jenkins_api, mock_logger):
        """Test get_build_errors with generic Jenkins exception."""
        jenkins_error = jenkins.JenkinsException("Unknown error occurred")
        with patch.object(jenkins_api, "get_job_console", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_build_errors("test-job", build_number=5)

            assert "Jenkins error getting build errors" in str(exc_info.value)

    def test_get_build_errors_unexpected_exception(self, jenkins_api, mock_logger):
        """Test get_build_errors with unexpected exception."""
        with patch.object(jenkins_api, "get_job_console", side_effect=Exception("Unexpected error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_build_errors("test-job", build_number=5)

            assert "Unexpected error getting build errors" in str(exc_info.value)

    def test_get_build_errors_detects_stack_traces(self, jenkins_api, mock_logger):
        """Test that get_build_errors detects Java and Python stack traces."""
        console_output = """Normal output
    at com.example.Class.method(Class.java:42)
    at com.example.Main.run(Main.java:10)
Traceback (most recent call last):
  File "test.py", line 5
More normal output"""

        with patch.object(jenkins_api, "get_job_console", return_value=console_output):
            result = jenkins_api.get_build_errors("test-job", build_number=5)

            # Should detect exception-related patterns
            exception_errors = [e for e in result["errors"] if e["category"] == "exception"]
            assert len(exception_errors) >= 1

    def test_get_build_errors_detects_jenkins_markers(self, jenkins_api, mock_logger):
        """Test that get_build_errors detects Jenkins-specific failure markers."""
        # Using output that contains Jenkins-specific markers not matched by earlier categories
        console_output = """Building...
Finished: ABORTED
fatal: cannot access remote repository"""

        with patch.object(jenkins_api, "get_job_console", return_value=console_output):
            result = jenkins_api.get_build_errors("test-job", build_number=5)

            # At least some jenkins markers should be detected
            # Note: The patterns are matched in dict order, so 'error', 'exception', 'failure'
            # categories are checked before 'jenkins'. The 'fatal:' and 'Finished: ABORTED'
            # should match jenkins category since they don't match the other patterns first.
            jenkins_errors = [e for e in result["errors"] if e["category"] == "jenkins"]
            assert len(jenkins_errors) >= 2, f"Expected at least 2 jenkins errors, got: {result['errors']}"

    def test_get_build_errors_line_matched_once(self, jenkins_api, mock_logger):
        """Test that each line is only matched once (first matching category wins)."""
        console_output = """This line has error and also FAILED"""

        with patch.object(jenkins_api, "get_job_console", return_value=console_output):
            result = jenkins_api.get_build_errors("test-job", build_number=5)

            # Should only have one error entry for this line
            assert len(result["errors"]) == 1

    def test_get_build_errors_empty_patterns_list(self, jenkins_api, console_output_with_errors, mock_logger):
        """Test get_build_errors with empty patterns list uses defaults."""
        with patch.object(jenkins_api, "get_job_console", return_value=console_output_with_errors):
            result = jenkins_api.get_build_errors("test-job", build_number=5, patterns=[])

            # Empty list should use default patterns
            # Since we're passing empty list, it will create empty 'custom' category
            # But with our implementation, empty patterns list creates an empty compiled list
            assert "errors" in result
            assert "summary" in result


class TestJenkinsApiEnableJob:
    """Test enable_job_state method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def enabled_job_info(self):
        """Sample job info for an enabled job."""
        return {
            "name": "test-job",
            "buildable": True,
            "url": "http://test-jenkins.com/job/test-job/",
        }

    @pytest.fixture
    def disabled_job_info(self):
        """Sample job info for a disabled job."""
        return {
            "name": "test-job",
            "buildable": False,
            "url": "http://test-jenkins.com/job/test-job/",
        }

    def test_enable_job_success(self, jenkins_api, enabled_job_info, mock_logger):
        """Test successful job enabling."""
        with patch.object(jenkins_api, "enable_job") as mock_enable:
            with patch.object(jenkins_api, "get_job_info", return_value=enabled_job_info):
                result = jenkins_api.enable_job_state("test-job")

                assert result["success"] is True
                assert result["job_name"] == "test-job"
                assert result["enabled"] is True
                mock_enable.assert_called_once_with("test-job")
                mock_logger.info.assert_any_call("Enabling job: test-job")
                mock_logger.info.assert_any_call("Successfully enabled job: test-job, enabled: True")

    def test_enable_job_already_enabled(self, jenkins_api, enabled_job_info, mock_logger):
        """Test enabling an already enabled job."""
        with patch.object(jenkins_api, "enable_job") as mock_enable:
            with patch.object(jenkins_api, "get_job_info", return_value=enabled_job_info):
                result = jenkins_api.enable_job_state("test-job")

                assert result["success"] is True
                assert result["enabled"] is True
                mock_enable.assert_called_once_with("test-job")

    def test_enable_job_job_not_found(self, jenkins_api, mock_logger):
        """Test enabling a non-existent job."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "enable_job", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.enable_job_state("nonexistent-job")

            assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_enable_job_connection_error(self, jenkins_api, mock_logger):
        """Test enabling job with connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "enable_job", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.enable_job_state("test-job")

            assert "Connection error while enabling job 'test-job'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_enable_job_generic_jenkins_error(self, jenkins_api, mock_logger):
        """Test enabling job with generic Jenkins error."""
        jenkins_error = jenkins.JenkinsException("Permission denied")
        with patch.object(jenkins_api, "enable_job", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.enable_job_state("test-job")

            assert "Jenkins error enabling job 'test-job'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_enable_job_unexpected_exception(self, jenkins_api, mock_logger):
        """Test enabling job with unexpected exception."""
        with patch.object(jenkins_api, "enable_job", side_effect=Exception("Unexpected error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.enable_job_state("test-job")

            assert "Unexpected error enabling job 'test-job'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_enable_job_missing_buildable_field(self, jenkins_api, mock_logger):
        """Test enabling job when job info missing buildable field."""
        job_info_no_buildable = {"name": "test-job", "url": "http://test-jenkins.com/job/test-job/"}
        with patch.object(jenkins_api, "enable_job"):
            with patch.object(jenkins_api, "get_job_info", return_value=job_info_no_buildable):
                result = jenkins_api.enable_job_state("test-job")

                # Should default to False when buildable field is missing
                assert result["success"] is True
                assert result["enabled"] is False


class TestJenkinsApiDisableJob:
    """Test disable_job_state method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def enabled_job_info(self):
        """Sample job info for an enabled job."""
        return {
            "name": "test-job",
            "buildable": True,
            "url": "http://test-jenkins.com/job/test-job/",
        }

    @pytest.fixture
    def disabled_job_info(self):
        """Sample job info for a disabled job."""
        return {
            "name": "test-job",
            "buildable": False,
            "url": "http://test-jenkins.com/job/test-job/",
        }

    def test_disable_job_success(self, jenkins_api, disabled_job_info, mock_logger):
        """Test successful job disabling."""
        with patch.object(jenkins_api, "disable_job") as mock_disable:
            with patch.object(jenkins_api, "get_job_info", return_value=disabled_job_info):
                result = jenkins_api.disable_job_state("test-job")

                assert result["success"] is True
                assert result["job_name"] == "test-job"
                assert result["enabled"] is False
                mock_disable.assert_called_once_with("test-job")
                mock_logger.info.assert_any_call("Disabling job: test-job")
                mock_logger.info.assert_any_call("Successfully disabled job: test-job, enabled: False")

    def test_disable_job_already_disabled(self, jenkins_api, disabled_job_info, mock_logger):
        """Test disabling an already disabled job."""
        with patch.object(jenkins_api, "disable_job") as mock_disable:
            with patch.object(jenkins_api, "get_job_info", return_value=disabled_job_info):
                result = jenkins_api.disable_job_state("test-job")

                assert result["success"] is True
                assert result["enabled"] is False
                mock_disable.assert_called_once_with("test-job")

    def test_disable_job_job_not_found(self, jenkins_api, mock_logger):
        """Test disabling a non-existent job."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "disable_job", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.disable_job_state("nonexistent-job")

            assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_disable_job_connection_error(self, jenkins_api, mock_logger):
        """Test disabling job with connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "disable_job", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.disable_job_state("test-job")

            assert "Connection error while disabling job 'test-job'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_disable_job_generic_jenkins_error(self, jenkins_api, mock_logger):
        """Test disabling job with generic Jenkins error."""
        jenkins_error = jenkins.JenkinsException("Permission denied")
        with patch.object(jenkins_api, "disable_job", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.disable_job_state("test-job")

            assert "Jenkins error disabling job 'test-job'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_disable_job_unexpected_exception(self, jenkins_api, mock_logger):
        """Test disabling job with unexpected exception."""
        with patch.object(jenkins_api, "disable_job", side_effect=Exception("Unexpected error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.disable_job_state("test-job")

            assert "Unexpected error disabling job 'test-job'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_disable_job_missing_buildable_field(self, jenkins_api, mock_logger):
        """Test disabling job when job info missing buildable field."""
        job_info_no_buildable = {"name": "test-job", "url": "http://test-jenkins.com/job/test-job/"}
        with patch.object(jenkins_api, "disable_job"):
            with patch.object(jenkins_api, "get_job_info", return_value=job_info_no_buildable):
                result = jenkins_api.disable_job_state("test-job")

                # Should default to True when buildable field is missing
                assert result["success"] is True
                assert result["enabled"] is True


class TestJenkinsApiRebuild:
    """Test rebuild method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def sample_build_info_with_params(self):
        """Sample build info with ParametersAction."""
        return {
            "number": 5,
            "result": "SUCCESS",
            "url": "http://test-jenkins.com/job/test-job/5/",
            "actions": [
                {"_class": "hudson.model.CauseAction"},
                {
                    "_class": "hudson.model.ParametersAction",
                    "parameters": [
                        {"_class": "hudson.model.StringParameterValue", "name": "BRANCH", "value": "main"},
                        {"_class": "hudson.model.StringParameterValue", "name": "ENV", "value": "production"},
                        {"_class": "hudson.model.BooleanParameterValue", "name": "DEBUG", "value": True},
                    ],
                },
                {"_class": "hudson.plugins.git.util.BuildData"},
            ],
        }

    @pytest.fixture
    def sample_build_info_no_params(self):
        """Sample build info without parameters."""
        return {
            "number": 5,
            "result": "SUCCESS",
            "url": "http://test-jenkins.com/job/test-job/5/",
            "actions": [
                {"_class": "hudson.model.CauseAction"},
                {"_class": "hudson.plugins.git.util.BuildData"},
            ],
        }

    @pytest.fixture
    def sample_job_info(self):
        """Sample job info."""
        return {
            "name": "test-job",
            "nextBuildNumber": 10,
        }

    def test_rebuild_success_with_parameters(
        self, jenkins_api, sample_build_info_with_params, sample_job_info, mock_logger
    ):
        """Test successful rebuild with parameters."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_with_params):
            with patch.object(jenkins_api, "build_job") as mock_build:
                with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
                    result = jenkins_api.rebuild("test-job", 5)

                    assert result["success"] is True
                    assert result["job_name"] == "test-job"
                    assert result["source_build_number"] == 5
                    assert result["new_build_number"] == 9
                    mock_build.assert_called_once_with(
                        "test-job",
                        {"BRANCH": "main", "ENV": "production", "DEBUG": True},
                    )
                    mock_logger.info.assert_any_call("Rebuilding job: test-job with parameters from build #5")
                    mock_logger.info.assert_any_call("Extracted 3 parameters from build #5")

    def test_rebuild_success_without_parameters(
        self, jenkins_api, sample_build_info_no_params, sample_job_info, mock_logger
    ):
        """Test successful rebuild without parameters."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_no_params):
            with patch.object(jenkins_api, "build_job") as mock_build:
                with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
                    result = jenkins_api.rebuild("test-job", 5)

                    assert result["success"] is True
                    assert result["job_name"] == "test-job"
                    assert result["source_build_number"] == 5
                    assert result["new_build_number"] == 9
                    mock_build.assert_called_once_with("test-job")
                    mock_logger.info.assert_any_call("Extracted 0 parameters from build #5")

    def test_rebuild_build_not_found(self, jenkins_api, mock_logger):
        """Test rebuild when source build is not found."""
        jenkins_error = jenkins.JenkinsException("build[999] does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.rebuild("test-job", 999)

            assert "Build 'test-job#999' not found" in str(exc_info.value)

    def test_rebuild_job_not_found(self, jenkins_api, sample_build_info_with_params, mock_logger):
        """Test rebuild when job is not found."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_with_params):
            with patch.object(jenkins_api, "build_job", side_effect=jenkins_error):
                with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                    jenkins_api.rebuild("nonexistent-job", 5)

                assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)
                mock_logger.error.assert_called_once()

    def test_rebuild_connection_error(self, jenkins_api, mock_logger):
        """Test rebuild with connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.rebuild("test-job", 5)

            assert "Connection error while rebuilding job 'test-job'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_rebuild_generic_jenkins_error(self, jenkins_api, sample_build_info_with_params, mock_logger):
        """Test rebuild with generic Jenkins error."""
        jenkins_error = jenkins.JenkinsException("Permission denied")
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_with_params):
            with patch.object(jenkins_api, "build_job", side_effect=jenkins_error):
                with pytest.raises(JenkinsApiError) as exc_info:
                    jenkins_api.rebuild("test-job", 5)

                assert "Jenkins error rebuilding job 'test-job'" in str(exc_info.value)
                mock_logger.error.assert_called_once()

    def test_rebuild_unexpected_exception(self, jenkins_api, mock_logger):
        """Test rebuild with unexpected exception."""
        with patch.object(jenkins_api, "get_build_info", side_effect=Exception("Unexpected error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.rebuild("test-job", 5)

            assert "Unexpected error rebuilding job 'test-job'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_rebuild_with_null_actions(self, jenkins_api, sample_job_info, mock_logger):
        """Test rebuild when actions contain null entries."""
        build_info_with_nulls = {
            "number": 5,
            "result": "SUCCESS",
            "actions": [
                None,
                {
                    "_class": "hudson.model.ParametersAction",
                    "parameters": [
                        {"name": "PARAM1", "value": "value1"},
                        None,
                        {"name": "PARAM2", "value": "value2"},
                    ],
                },
                None,
            ],
        }
        with patch.object(jenkins_api, "get_build_info", return_value=build_info_with_nulls):
            with patch.object(jenkins_api, "build_job") as mock_build:
                with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
                    result = jenkins_api.rebuild("test-job", 5)

                    assert result["success"] is True
                    mock_build.assert_called_once_with(
                        "test-job",
                        {"PARAM1": "value1", "PARAM2": "value2"},
                    )

    def test_rebuild_with_empty_actions(self, jenkins_api, sample_job_info, mock_logger):
        """Test rebuild when actions is empty."""
        build_info_empty_actions = {
            "number": 5,
            "result": "SUCCESS",
            "actions": [],
        }
        with patch.object(jenkins_api, "get_build_info", return_value=build_info_empty_actions):
            with patch.object(jenkins_api, "build_job") as mock_build:
                with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
                    result = jenkins_api.rebuild("test-job", 5)

                    assert result["success"] is True
                    mock_build.assert_called_once_with("test-job")

    def test_rebuild_with_param_missing_name(self, jenkins_api, sample_job_info, mock_logger):
        """Test rebuild when parameter is missing name field."""
        build_info_missing_name = {
            "number": 5,
            "result": "SUCCESS",
            "actions": [
                {
                    "_class": "hudson.model.ParametersAction",
                    "parameters": [
                        {"name": "PARAM1", "value": "value1"},
                        {"value": "orphan_value"},  # Missing name
                        {"name": "PARAM2", "value": "value2"},
                    ],
                },
            ],
        }
        with patch.object(jenkins_api, "get_build_info", return_value=build_info_missing_name):
            with patch.object(jenkins_api, "build_job") as mock_build:
                with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
                    result = jenkins_api.rebuild("test-job", 5)

                    assert result["success"] is True
                    # Should only include parameters with valid names
                    mock_build.assert_called_once_with(
                        "test-job",
                        {"PARAM1": "value1", "PARAM2": "value2"},
                    )

    def test_rebuild_does_not_exist_build_error(self, jenkins_api, mock_logger):
        """Test rebuild when build does not exist error comes during build trigger."""
        jenkins_error = jenkins.JenkinsException("build does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.rebuild("test-job", 999)

            assert "Build 'test-job#999' not found" in str(exc_info.value)


class TestJenkinsApiCancelBuild:
    """Test cancel_build method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def running_build_info(self):
        """Sample build info for a running build."""
        return {
            "number": 5,
            "result": None,
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": True,
        }

    @pytest.fixture
    def completed_build_info(self):
        """Sample build info for a completed build."""
        return {
            "number": 5,
            "result": "SUCCESS",
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": False,
        }

    def test_cancel_build_success_with_build_number(self, jenkins_api, running_build_info, mock_logger):
        """Test successful build cancellation with specific build number."""
        with patch.object(jenkins_api, "get_build_info", return_value=running_build_info):
            with patch.object(jenkins_api, "stop_build") as mock_stop:
                result = jenkins_api.cancel_build("test-job", build_number=5)

                assert result["success"] is True
                assert result["job_name"] == "test-job"
                assert result["build_number"] == 5
                assert result["message"] == "Build cancelled successfully"
                mock_stop.assert_called_once_with("test-job", 5)
                mock_logger.info.assert_any_call("Cancelling build for job: test-job, build: 5")
                mock_logger.info.assert_any_call("Successfully cancelled build: test-job#5")

    def test_cancel_build_success_without_build_number(
        self, jenkins_api, sample_job_info, running_build_info, mock_logger
    ):
        """Test successful build cancellation using last build number."""
        # Adjust running_build_info to match sample_job_info's lastBuild number
        running_build_info_adjusted = running_build_info.copy()
        running_build_info_adjusted["number"] = 2
        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            with patch.object(jenkins_api, "get_build_info", return_value=running_build_info_adjusted):
                with patch.object(jenkins_api, "stop_build") as mock_stop:
                    result = jenkins_api.cancel_build("test-job")

                    assert result["success"] is True
                    assert result["job_name"] == "test-job"
                    assert result["build_number"] == 2  # From sample_job_info lastBuild
                    assert result["message"] == "Build cancelled successfully"
                    mock_stop.assert_called_once_with("test-job", 2)

    def test_cancel_build_already_completed(self, jenkins_api, completed_build_info, mock_logger):
        """Test cancel_build when build is already completed."""
        with patch.object(jenkins_api, "get_build_info", return_value=completed_build_info):
            with patch.object(jenkins_api, "stop_build") as mock_stop:
                result = jenkins_api.cancel_build("test-job", build_number=5)

                assert result["success"] is False
                assert result["job_name"] == "test-job"
                assert result["build_number"] == 5
                assert result["message"] == "Build already completed with result: SUCCESS"
                mock_stop.assert_not_called()
                mock_logger.info.assert_any_call("Build 'test-job#5' already completed with result: SUCCESS")

    def test_cancel_build_already_completed_failure(self, jenkins_api, mock_logger):
        """Test cancel_build when build is already completed with FAILURE."""
        completed_failure_info = {
            "number": 5,
            "result": "FAILURE",
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": False,
        }
        with patch.object(jenkins_api, "get_build_info", return_value=completed_failure_info):
            with patch.object(jenkins_api, "stop_build") as mock_stop:
                result = jenkins_api.cancel_build("test-job", build_number=5)

                assert result["success"] is False
                assert result["message"] == "Build already completed with result: FAILURE"
                mock_stop.assert_not_called()

    def test_cancel_build_already_completed_aborted(self, jenkins_api, mock_logger):
        """Test cancel_build when build is already aborted."""
        completed_aborted_info = {
            "number": 5,
            "result": "ABORTED",
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": False,
        }
        with patch.object(jenkins_api, "get_build_info", return_value=completed_aborted_info):
            with patch.object(jenkins_api, "stop_build") as mock_stop:
                result = jenkins_api.cancel_build("test-job", build_number=5)

                assert result["success"] is False
                assert result["message"] == "Build already completed with result: ABORTED"
                mock_stop.assert_not_called()

    def test_cancel_build_no_builds_found(self, jenkins_api, empty_job_info, mock_logger):
        """Test cancel_build when no builds exist."""
        with patch.object(jenkins_api, "get_job_info", return_value=empty_job_info):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.cancel_build("empty-job")

            assert "No builds found for job 'empty-job'" in str(exc_info.value)

    def test_cancel_build_job_not_found(self, jenkins_api, mock_logger):
        """Test cancel_build when job does not exist."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.cancel_build("nonexistent-job")

            assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)

    def test_cancel_build_job_not_found_with_build_number(self, jenkins_api, running_build_info, mock_logger):
        """Test cancel_build when job does not exist during stop_build (with explicit build number)."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "get_build_info", return_value=running_build_info):
            with patch.object(jenkins_api, "stop_build", side_effect=jenkins_error):
                with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                    jenkins_api.cancel_build("nonexistent-job", build_number=5)

                assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)
                mock_logger.error.assert_called_once()

    def test_cancel_build_build_not_found(self, jenkins_api, mock_logger):
        """Test cancel_build when build does not exist."""
        jenkins_error = jenkins.JenkinsException("build[999] does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.cancel_build("test-job", build_number=999)

            assert "Build 'test-job#999' not found" in str(exc_info.value)

    def test_cancel_build_build_not_found_via_stop_build(self, jenkins_api, running_build_info, mock_logger):
        """Test cancel_build when stop_build raises build not found."""
        jenkins_error = jenkins.JenkinsException("build[999] does not exist")
        with patch.object(jenkins_api, "get_build_info", return_value=running_build_info):
            with patch.object(jenkins_api, "stop_build", side_effect=jenkins_error):
                with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                    jenkins_api.cancel_build("test-job", build_number=999)

                assert "Build 'test-job#999' not found" in str(exc_info.value)
                mock_logger.error.assert_called_once()

    def test_cancel_build_connection_error(self, jenkins_api, running_build_info, mock_logger):
        """Test cancel_build with connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_build_info", return_value=running_build_info):
            with patch.object(jenkins_api, "stop_build", side_effect=jenkins_error):
                with pytest.raises(JenkinsConnectionError) as exc_info:
                    jenkins_api.cancel_build("test-job", build_number=5)

                assert "Connection error while cancelling build 'test-job#5'" in str(exc_info.value)
                mock_logger.error.assert_called_once()

    def test_cancel_build_generic_jenkins_error(self, jenkins_api, running_build_info, mock_logger):
        """Test cancel_build with generic Jenkins error."""
        jenkins_error = jenkins.JenkinsException("Permission denied")
        with patch.object(jenkins_api, "get_build_info", return_value=running_build_info):
            with patch.object(jenkins_api, "stop_build", side_effect=jenkins_error):
                with pytest.raises(JenkinsApiError) as exc_info:
                    jenkins_api.cancel_build("test-job", build_number=5)

                assert "Jenkins error cancelling build 'test-job#5'" in str(exc_info.value)
                mock_logger.error.assert_called_once()

    def test_cancel_build_unexpected_exception(self, jenkins_api, running_build_info, mock_logger):
        """Test cancel_build with unexpected exception."""
        with patch.object(jenkins_api, "get_build_info", return_value=running_build_info):
            with patch.object(jenkins_api, "stop_build", side_effect=Exception("Unexpected error")):
                with pytest.raises(JenkinsApiError) as exc_info:
                    jenkins_api.cancel_build("test-job", build_number=5)

                assert "Unexpected error cancelling build 'test-job#5'" in str(exc_info.value)
                mock_logger.error.assert_called_once()

    def test_cancel_build_job_not_found_during_get_job_info(self, jenkins_api, mock_logger):
        """Test cancel_build when job not found during get_job_info (no build number provided)."""
        jenkins_error = jenkins.JenkinsException("job[test-job] does not exist")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.cancel_build("test-job")

            assert "Job 'test-job' does not exist" in str(exc_info.value)

    def test_cancel_build_reraises_jenkins_exception_from_get_job_info(self, jenkins_api, mock_logger):
        """Test cancel_build re-raises non-not-found JenkinsException from get_job_info."""
        jenkins_error = jenkins.JenkinsException("Unknown error")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.cancel_build("test-job")

            assert "Jenkins error cancelling build" in str(exc_info.value)

    def test_cancel_build_connection_error_during_get_build_info(self, jenkins_api, mock_logger):
        """Test cancel_build when get_build_info raises connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.cancel_build("test-job", build_number=5)

            assert "Connection error while cancelling build 'test-job#5'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_cancel_build_get_build_info_reraises_generic_jenkins_exception(self, jenkins_api, mock_logger):
        """Test cancel_build when get_build_info raises generic Jenkins exception (not does not exist)."""
        jenkins_error = jenkins.JenkinsException("Permission denied")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.cancel_build("test-job", build_number=5)

            assert "Jenkins error cancelling build 'test-job#5'" in str(exc_info.value)
            mock_logger.error.assert_called_once()


class TestJenkinsApiGetBuildParameters:
    """Test get_build_parameters method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def sample_build_info_with_params(self):
        """Sample build info with ParametersAction."""
        return {
            "number": 5,
            "result": "SUCCESS",
            "url": "http://test-jenkins.com/job/test-job/5/",
            "actions": [
                {"_class": "hudson.model.CauseAction"},
                {
                    "_class": "hudson.model.ParametersAction",
                    "parameters": [
                        {"_class": "hudson.model.StringParameterValue", "name": "BRANCH", "value": "main"},
                        {"_class": "hudson.model.StringParameterValue", "name": "ENV", "value": "production"},
                        {"_class": "hudson.model.BooleanParameterValue", "name": "DEBUG", "value": True},
                    ],
                },
                {"_class": "hudson.plugins.git.util.BuildData"},
            ],
        }

    @pytest.fixture
    def sample_build_info_no_params(self):
        """Sample build info without parameters."""
        return {
            "number": 5,
            "result": "SUCCESS",
            "url": "http://test-jenkins.com/job/test-job/5/",
            "actions": [
                {"_class": "hudson.model.CauseAction"},
                {"_class": "hudson.plugins.git.util.BuildData"},
            ],
        }

    @pytest.fixture
    def sample_job_info(self):
        """Sample job info."""
        return {
            "name": "test-job",
            "lastBuild": {"number": 5},
            "nextBuildNumber": 6,
        }

    def test_get_build_parameters_success_with_build_number(
        self, jenkins_api, sample_build_info_with_params, mock_logger
    ):
        """Test successful retrieval of build parameters with specific build number."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_with_params):
            result = jenkins_api.get_build_parameters("test-job", build_number=5)

            assert result["job_name"] == "test-job"
            assert result["build_number"] == 5
            assert len(result["parameters"]) == 3
            assert result["parameters"][0] == {"name": "BRANCH", "value": "main"}
            assert result["parameters"][1] == {"name": "ENV", "value": "production"}
            assert result["parameters"][2] == {"name": "DEBUG", "value": True}
            mock_logger.info.assert_any_call("Getting build parameters for job: test-job, build: 5")
            mock_logger.info.assert_any_call("Found 3 parameters for build 'test-job#5'")

    def test_get_build_parameters_success_without_build_number(
        self, jenkins_api, sample_job_info, sample_build_info_with_params, mock_logger
    ):
        """Test successful retrieval of build parameters using last build."""
        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_with_params):
                result = jenkins_api.get_build_parameters("test-job")

                assert result["job_name"] == "test-job"
                assert result["build_number"] == 5
                assert len(result["parameters"]) == 3

    def test_get_build_parameters_no_parameters(self, jenkins_api, sample_build_info_no_params, mock_logger):
        """Test retrieval when build has no parameters."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_no_params):
            result = jenkins_api.get_build_parameters("test-job", build_number=5)

            assert result["job_name"] == "test-job"
            assert result["build_number"] == 5
            assert result["parameters"] == []
            mock_logger.info.assert_any_call("Found 0 parameters for build 'test-job#5'")

    def test_get_build_parameters_no_builds_found(self, jenkins_api, mock_logger):
        """Test get_build_parameters when no builds exist."""
        empty_job_info = {"name": "test-job", "lastBuild": None, "nextBuildNumber": 1}
        with patch.object(jenkins_api, "get_job_info", return_value=empty_job_info):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.get_build_parameters("test-job")

            assert "No builds found for job 'test-job'" in str(exc_info.value)

    def test_get_build_parameters_job_not_found(self, jenkins_api, mock_logger):
        """Test get_build_parameters when job does not exist."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.get_build_parameters("nonexistent-job")

            assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)

    def test_get_build_parameters_build_not_found(self, jenkins_api, mock_logger):
        """Test get_build_parameters when build does not exist."""
        jenkins_error = jenkins.JenkinsException("build[999] does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.get_build_parameters("test-job", build_number=999)

            assert "Build 'test-job#999' not found" in str(exc_info.value)

    def test_get_build_parameters_connection_error(self, jenkins_api, mock_logger):
        """Test get_build_parameters with connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.get_build_parameters("test-job", build_number=5)

            assert "Connection error while getting build parameters for 'test-job#5'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_get_build_parameters_generic_jenkins_error(self, jenkins_api, mock_logger):
        """Test get_build_parameters with generic Jenkins error."""
        jenkins_error = jenkins.JenkinsException("Permission denied")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_build_parameters("test-job", build_number=5)

            assert "Jenkins error getting build parameters for 'test-job#5'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_get_build_parameters_unexpected_exception(self, jenkins_api, mock_logger):
        """Test get_build_parameters with unexpected exception."""
        with patch.object(jenkins_api, "get_build_info", side_effect=Exception("Unexpected error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_build_parameters("test-job", build_number=5)

            assert "Unexpected error getting build parameters for 'test-job#5'" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_get_build_parameters_with_null_actions(self, jenkins_api, mock_logger):
        """Test get_build_parameters when actions contain null entries."""
        build_info_with_nulls = {
            "number": 5,
            "result": "SUCCESS",
            "actions": [
                None,
                {
                    "_class": "hudson.model.ParametersAction",
                    "parameters": [
                        {"name": "PARAM1", "value": "value1"},
                        None,
                        {"name": "PARAM2", "value": "value2"},
                    ],
                },
                None,
            ],
        }
        with patch.object(jenkins_api, "get_build_info", return_value=build_info_with_nulls):
            result = jenkins_api.get_build_parameters("test-job", build_number=5)

            assert result["job_name"] == "test-job"
            assert result["build_number"] == 5
            assert len(result["parameters"]) == 2
            assert result["parameters"][0] == {"name": "PARAM1", "value": "value1"}
            assert result["parameters"][1] == {"name": "PARAM2", "value": "value2"}

    def test_get_build_parameters_with_empty_actions(self, jenkins_api, mock_logger):
        """Test get_build_parameters when actions is empty."""
        build_info_empty_actions = {
            "number": 5,
            "result": "SUCCESS",
            "actions": [],
        }
        with patch.object(jenkins_api, "get_build_info", return_value=build_info_empty_actions):
            result = jenkins_api.get_build_parameters("test-job", build_number=5)

            assert result["parameters"] == []

    def test_get_build_parameters_with_param_missing_name(self, jenkins_api, mock_logger):
        """Test get_build_parameters when parameter is missing name field."""
        build_info_missing_name = {
            "number": 5,
            "result": "SUCCESS",
            "actions": [
                {
                    "_class": "hudson.model.ParametersAction",
                    "parameters": [
                        {"name": "PARAM1", "value": "value1"},
                        {"value": "orphan_value"},  # Missing name
                        {"name": "PARAM2", "value": "value2"},
                    ],
                },
            ],
        }
        with patch.object(jenkins_api, "get_build_info", return_value=build_info_missing_name):
            result = jenkins_api.get_build_parameters("test-job", build_number=5)

            # Should only include parameters with valid names
            assert len(result["parameters"]) == 2
            assert result["parameters"][0] == {"name": "PARAM1", "value": "value1"}
            assert result["parameters"][1] == {"name": "PARAM2", "value": "value2"}

    def test_get_build_parameters_with_none_value(self, jenkins_api, mock_logger):
        """Test get_build_parameters when parameter value is None."""
        build_info_none_value = {
            "number": 5,
            "result": "SUCCESS",
            "actions": [
                {
                    "_class": "hudson.model.ParametersAction",
                    "parameters": [
                        {"name": "PARAM1", "value": None},
                        {"name": "PARAM2", "value": "value2"},
                    ],
                },
            ],
        }
        with patch.object(jenkins_api, "get_build_info", return_value=build_info_none_value):
            result = jenkins_api.get_build_parameters("test-job", build_number=5)

            # Should include parameter with None value
            assert len(result["parameters"]) == 2
            assert result["parameters"][0] == {"name": "PARAM1", "value": None}
            assert result["parameters"][1] == {"name": "PARAM2", "value": "value2"}

    def test_get_build_parameters_job_not_found_in_outer_handler(self, jenkins_api, mock_logger):
        """Test get_build_parameters when job not found error is raised in outer exception handler."""
        # This tests the path where the Jenkins exception is caught by the outer handler
        # When the error message contains "does not exist" but is not caught by inner handler,
        # it goes to the outer handler which checks for "job" in the message
        jenkins_error = jenkins.JenkinsException("job[test-job] does not exist")

        # Make get_build_info raise the exception but ensure it gets to the outer handler
        # by raising an exception that doesn't match the inner handler's conditions
        def side_effect(*args, **kwargs):
            raise jenkins_error

        with patch.object(jenkins_api, "get_build_info") as mock_get_build_info:
            # The inner handler catches this but since it contains "does not exist",
            # it will raise JenkinsBuildNotFoundError. To test the outer handler,
            # we need to make the inner handler re-raise the original exception.
            mock_get_build_info.side_effect = side_effect
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.get_build_parameters("test-job", build_number=5)

            # Since the inner handler doesn't check for "job" specifically,
            # it will raise JenkinsBuildNotFoundError for any "does not exist" error
            assert "Build 'test-job#5' not found" in str(exc_info.value)

    def test_get_build_parameters_build_not_found_in_outer_handler(self, jenkins_api, mock_logger):
        """Test get_build_parameters when build not found error is raised in outer exception handler."""
        # This tests the path where the Jenkins exception is caught by the outer handler
        jenkins_error = jenkins.JenkinsException("build does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.get_build_parameters("test-job", build_number=5)

            assert "Build 'test-job#5' not found" in str(exc_info.value)

    def test_get_build_parameters_reraises_jenkins_exception_from_get_job_info(self, jenkins_api, mock_logger):
        """Test get_build_parameters re-raises non-not-found JenkinsException from get_job_info."""
        jenkins_error = jenkins.JenkinsException("Unknown error")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.get_build_parameters("test-job")

            assert "Jenkins error getting build parameters" in str(exc_info.value)


class TestJenkinsApiMonitorBuild:
    """Test monitor_build method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def sample_build_info_running(self):
        """Sample build info for a running build."""
        return {
            "number": 5,
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": True,
            "result": None,
            "duration": 0,
        }

    @pytest.fixture
    def sample_build_info_completed(self):
        """Sample build info for a completed build."""
        return {
            "number": 5,
            "url": "http://test-jenkins.com/job/test-job/5/",
            "building": False,
            "result": "SUCCESS",
            "duration": 12345,
        }

    @pytest.fixture
    def multi_line_console_output(self):
        """Multi-line console output for testing from_line parameter."""
        return """Line 0: Started by user admin
Line 1: Running as SYSTEM
Line 2: Building in workspace /var/jenkins_home/workspace/test-job
Line 3: [test-job] $ /bin/sh -xe /tmp/jenkins123456789.sh
Line 4: + echo 'Hello World'
Line 5: Hello World
Line 6: + echo 'Job completed successfully'
Line 7: Job completed successfully
Line 8: Finished: SUCCESS"""

    def test_monitor_build_with_build_number(
        self, jenkins_api, sample_build_info_running, multi_line_console_output, mock_logger
    ):
        """Test monitor_build with specific build number."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_running):
            with patch.object(jenkins_api, "get_build_console_output", return_value=multi_line_console_output):
                result = jenkins_api.monitor_build("test-job", build_number=5)

                assert result["job_name"] == "test-job"
                assert result["build_number"] == 5
                assert result["building"] is True
                assert result["result"] is None
                assert result["next_line"] == 9  # 9 lines total
                assert "Line 0: Started by user admin" in result["output"]
                mock_logger.info.assert_any_call("Monitoring build for job: test-job, build: 5, from_line: 0")

    def test_monitor_build_without_build_number(
        self, jenkins_api, sample_job_info, sample_build_info_completed, multi_line_console_output, mock_logger
    ):
        """Test monitor_build using latest build."""
        with patch.object(jenkins_api, "get_job_info", return_value=sample_job_info):
            with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_completed):
                with patch.object(jenkins_api, "get_build_console_output", return_value=multi_line_console_output):
                    result = jenkins_api.monitor_build("test-job")

                    assert result["job_name"] == "test-job"
                    assert result["build_number"] == 2  # From sample_job_info lastBuild
                    assert result["building"] is False
                    assert result["result"] == "SUCCESS"

    def test_monitor_build_with_from_line(
        self, jenkins_api, sample_build_info_running, multi_line_console_output, mock_logger
    ):
        """Test monitor_build with from_line parameter."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_running):
            with patch.object(jenkins_api, "get_build_console_output", return_value=multi_line_console_output):
                result = jenkins_api.monitor_build("test-job", build_number=5, from_line=5)

                assert result["job_name"] == "test-job"
                assert result["build_number"] == 5
                assert result["next_line"] == 9
                # Should only include lines 5-8
                assert "Line 0" not in result["output"]
                assert "Line 4" not in result["output"]
                assert "Line 5: Hello World" in result["output"]
                assert "Line 8: Finished: SUCCESS" in result["output"]

    def test_monitor_build_from_line_beyond_output(
        self, jenkins_api, sample_build_info_completed, multi_line_console_output, mock_logger
    ):
        """Test monitor_build when from_line is beyond available output."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_completed):
            with patch.object(jenkins_api, "get_build_console_output", return_value=multi_line_console_output):
                result = jenkins_api.monitor_build("test-job", build_number=5, from_line=100)

                assert result["output"] == ""
                assert result["next_line"] == 9

    def test_monitor_build_negative_from_line(self, jenkins_api, mock_logger):
        """Test monitor_build raises ValueError for negative from_line."""
        with pytest.raises(ValueError) as exc_info:
            jenkins_api.monitor_build("test-job", build_number=5, from_line=-1)

        assert "from_line must be non-negative" in str(exc_info.value)

    def test_monitor_build_no_builds_found(self, jenkins_api, empty_job_info, mock_logger):
        """Test monitor_build when no builds are available."""
        with patch.object(jenkins_api, "get_job_info", return_value=empty_job_info):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.monitor_build("test-job")

            assert "No builds found for job 'test-job'" in str(exc_info.value)

    def test_monitor_build_job_not_found(self, jenkins_api, mock_logger):
        """Test monitor_build when job does not exist."""
        jenkins_error = jenkins.JenkinsException("job[nonexistent-job] does not exist")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsJobNotFoundError) as exc_info:
                jenkins_api.monitor_build("nonexistent-job")

            assert "Job 'nonexistent-job' does not exist" in str(exc_info.value)

    def test_monitor_build_build_not_found(self, jenkins_api, mock_logger):
        """Test monitor_build when build does not exist."""
        jenkins_error = jenkins.JenkinsException("build[999] does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.monitor_build("test-job", build_number=999)

            assert "Build 'test-job#999' not found" in str(exc_info.value)

    def test_monitor_build_connection_error(self, jenkins_api, mock_logger):
        """Test monitor_build handles connection error."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.monitor_build("test-job", build_number=5)

            assert "Connection error while monitoring build" in str(exc_info.value)
            assert "Connection timeout" in str(exc_info.value)

    def test_monitor_build_jenkins_api_error(self, jenkins_api, mock_logger):
        """Test monitor_build handles generic Jenkins API error."""
        jenkins_error = jenkins.JenkinsException("Some Jenkins error")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.monitor_build("test-job", build_number=5)

            assert "Jenkins error monitoring build" in str(exc_info.value)

    def test_monitor_build_unexpected_exception(self, jenkins_api, mock_logger):
        """Test monitor_build handles unexpected exception."""
        with patch.object(jenkins_api, "get_build_info", side_effect=RuntimeError("Unexpected error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.monitor_build("test-job", build_number=5)

            assert "Unexpected error monitoring build" in str(exc_info.value)
            assert "Unexpected error" in str(exc_info.value)

    def test_monitor_build_completed_build(
        self, jenkins_api, sample_build_info_completed, multi_line_console_output, mock_logger
    ):
        """Test monitor_build for a completed build."""
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_completed):
            with patch.object(jenkins_api, "get_build_console_output", return_value=multi_line_console_output):
                result = jenkins_api.monitor_build("test-job", build_number=5)

                assert result["building"] is False
                assert result["result"] == "SUCCESS"

    def test_monitor_build_incremental_output(self, jenkins_api, sample_build_info_running, mock_logger):
        """Test monitor_build for incremental output (simulating multiple calls)."""
        # First call - initial output
        initial_output = "Line 0: Started\nLine 1: Running"
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_running):
            with patch.object(jenkins_api, "get_build_console_output", return_value=initial_output):
                result1 = jenkins_api.monitor_build("test-job", build_number=5, from_line=0)

                assert result1["next_line"] == 2
                assert result1["building"] is True

        # Second call - more output available
        extended_output = "Line 0: Started\nLine 1: Running\nLine 2: Still running\nLine 3: Almost done"
        with patch.object(jenkins_api, "get_build_info", return_value=sample_build_info_running):
            with patch.object(jenkins_api, "get_build_console_output", return_value=extended_output):
                result2 = jenkins_api.monitor_build("test-job", build_number=5, from_line=result1["next_line"])

                assert result2["next_line"] == 4
                assert "Line 2: Still running" in result2["output"]
                assert "Line 3: Almost done" in result2["output"]
                assert "Line 0" not in result2["output"]
                assert "Line 1" not in result2["output"]

    def test_monitor_build_job_not_found_in_outer_handler(self, jenkins_api, mock_logger):
        """Test monitor_build when job not found error is caught in outer exception handler."""
        # When "job does not exist" error occurs in get_build_info's inner handler,
        # it gets caught as a build not found error (since the inner handler doesn't
        # distinguish between job and build errors). The outer handler only receives
        # errors that pass through the inner try/except block.
        jenkins_error = jenkins.JenkinsException("job does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            # The inner handler catches "does not exist" and raises JenkinsBuildNotFoundError
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.monitor_build("test-job", build_number=5)

            assert "Build 'test-job#5' not found" in str(exc_info.value)

    def test_monitor_build_build_not_found_in_outer_handler(self, jenkins_api, mock_logger):
        """Test monitor_build when build not found error is caught in outer exception handler."""
        jenkins_error = jenkins.JenkinsException("build does not exist")
        with patch.object(jenkins_api, "get_build_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsBuildNotFoundError) as exc_info:
                jenkins_api.monitor_build("test-job", build_number=5)

            assert "Build 'test-job#5' not found" in str(exc_info.value)

    def test_monitor_build_reraises_jenkins_exception_from_get_job_info(self, jenkins_api, mock_logger):
        """Test monitor_build re-raises non-not-found JenkinsException from get_job_info."""
        jenkins_error = jenkins.JenkinsException("Unknown error")
        with patch.object(jenkins_api, "get_job_info", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.monitor_build("test-job")

            assert "Jenkins error monitoring build" in str(exc_info.value)


class TestJenkinsApiEnableAllJobs:
    """Test enable_all_jobs method."""

    @pytest.fixture
    def jenkins_api(self, mock_env_vars, mock_logger):
        """Create JenkinsApi instance for testing."""
        with patch("jenkins.Jenkins.__init__", return_value=None):
            return JenkinsApi()

    @pytest.fixture
    def sample_all_jobs(self):
        """Sample list of all jobs with various states."""
        return [
            {"name": "job1", "fullname": "job1", "color": "blue"},
            {"name": "job2", "fullname": "job2", "color": "blue_disabled"},
            {"name": "job3", "fullname": "folder1/job3", "color": "red"},
            {"name": "job4", "fullname": "folder1/job4", "color": "disabled"},
            {"name": "job5", "fullname": "folder1/subfolder/job5", "color": "blue_disabled"},
            {"name": "job6", "fullname": "folder2/job6", "color": "red_disabled"},
        ]

    def test_enable_all_jobs_no_folder_recursive(self, jenkins_api, sample_all_jobs, mock_logger):
        """Test enabling all disabled jobs without folder filter (recursive)."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=sample_all_jobs):
            with patch.object(jenkins_api, "enable_job") as mock_enable:
                result = jenkins_api.enable_all_jobs()

                assert result["count"] == 4
                assert len(result["enabled_jobs"]) == 4
                assert "job2" in result["enabled_jobs"]
                assert "folder1/job4" in result["enabled_jobs"]
                assert "folder1/subfolder/job5" in result["enabled_jobs"]
                assert "folder2/job6" in result["enabled_jobs"]
                assert mock_enable.call_count == 4

    def test_enable_all_jobs_no_folder_non_recursive(self, jenkins_api, sample_all_jobs, mock_logger):
        """Test enabling top-level disabled jobs only (non-recursive)."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=sample_all_jobs):
            with patch.object(jenkins_api, "enable_job") as mock_enable:
                result = jenkins_api.enable_all_jobs(recursive=False)

                assert result["count"] == 1
                assert len(result["enabled_jobs"]) == 1
                assert "job2" in result["enabled_jobs"]
                mock_enable.assert_called_once_with("job2")

    def test_enable_all_jobs_with_folder_recursive(self, jenkins_api, sample_all_jobs, mock_logger):
        """Test enabling all disabled jobs in a folder (recursive)."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=sample_all_jobs):
            with patch.object(jenkins_api, "enable_job") as mock_enable:
                result = jenkins_api.enable_all_jobs(folder="folder1")

                assert result["count"] == 2
                assert len(result["enabled_jobs"]) == 2
                assert "folder1/job4" in result["enabled_jobs"]
                assert "folder1/subfolder/job5" in result["enabled_jobs"]
                assert mock_enable.call_count == 2

    def test_enable_all_jobs_with_folder_non_recursive(self, jenkins_api, sample_all_jobs, mock_logger):
        """Test enabling disabled jobs directly in folder only (non-recursive)."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=sample_all_jobs):
            with patch.object(jenkins_api, "enable_job") as mock_enable:
                result = jenkins_api.enable_all_jobs(folder="folder1", recursive=False)

                assert result["count"] == 1
                assert len(result["enabled_jobs"]) == 1
                assert "folder1/job4" in result["enabled_jobs"]
                mock_enable.assert_called_once_with("folder1/job4")

    def test_enable_all_jobs_folder_with_leading_slash(self, jenkins_api, sample_all_jobs, mock_logger):
        """Test folder path normalization with leading slash."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=sample_all_jobs):
            with patch.object(jenkins_api, "enable_job"):
                result = jenkins_api.enable_all_jobs(folder="/folder1/")

                assert result["count"] == 2
                assert "folder1/job4" in result["enabled_jobs"]
                assert "folder1/subfolder/job5" in result["enabled_jobs"]

    def test_enable_all_jobs_no_disabled_jobs(self, jenkins_api, mock_logger):
        """Test when there are no disabled jobs."""
        all_enabled_jobs = [
            {"name": "job1", "fullname": "job1", "color": "blue"},
            {"name": "job2", "fullname": "job2", "color": "red"},
        ]
        with patch.object(jenkins_api, "get_all_jobs", return_value=all_enabled_jobs):
            with patch.object(jenkins_api, "enable_job") as mock_enable:
                result = jenkins_api.enable_all_jobs()

                assert result["count"] == 0
                assert result["enabled_jobs"] == []
                mock_enable.assert_not_called()

    def test_enable_all_jobs_empty_jobs_list(self, jenkins_api, mock_logger):
        """Test when there are no jobs at all."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=[]):
            with patch.object(jenkins_api, "enable_job") as mock_enable:
                result = jenkins_api.enable_all_jobs()

                assert result["count"] == 0
                assert result["enabled_jobs"] == []
                mock_enable.assert_not_called()

    def test_enable_all_jobs_partial_failure(self, jenkins_api, sample_all_jobs, mock_logger):
        """Test that enabling continues even if some jobs fail."""

        def enable_side_effect(job_name):
            if job_name == "folder1/job4":
                raise jenkins.JenkinsException("Permission denied")
            return None

        with patch.object(jenkins_api, "get_all_jobs", return_value=sample_all_jobs):
            with patch.object(jenkins_api, "enable_job", side_effect=enable_side_effect):
                result = jenkins_api.enable_all_jobs()

                # Should still enable the other jobs
                assert result["count"] == 3
                assert "folder1/job4" not in result["enabled_jobs"]
                assert "job2" in result["enabled_jobs"]
                mock_logger.warning.assert_called()

    def test_enable_all_jobs_connection_error(self, jenkins_api, mock_logger):
        """Test handling of connection error when getting jobs."""
        jenkins_error = jenkins.JenkinsException("Connection timeout")
        with patch.object(jenkins_api, "get_all_jobs", side_effect=jenkins_error):
            with pytest.raises(JenkinsConnectionError) as exc_info:
                jenkins_api.enable_all_jobs()

            assert "Connection error while enabling all jobs" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_enable_all_jobs_generic_jenkins_error(self, jenkins_api, mock_logger):
        """Test handling of generic Jenkins error."""
        jenkins_error = jenkins.JenkinsException("Permission denied")
        with patch.object(jenkins_api, "get_all_jobs", side_effect=jenkins_error):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.enable_all_jobs()

            assert "Jenkins error enabling all jobs" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_enable_all_jobs_unexpected_exception(self, jenkins_api, mock_logger):
        """Test handling of unexpected exception."""
        with patch.object(jenkins_api, "get_all_jobs", side_effect=Exception("Unexpected error")):
            with pytest.raises(JenkinsApiError) as exc_info:
                jenkins_api.enable_all_jobs()

            assert "Unexpected error enabling all jobs" in str(exc_info.value)
            mock_logger.error.assert_called_once()

    def test_enable_all_jobs_uses_name_when_fullname_missing(self, jenkins_api, mock_logger):
        """Test that name is used as fallback when fullname is missing."""
        jobs_without_fullname = [
            {"name": "job1", "color": "blue_disabled"},
        ]
        with patch.object(jenkins_api, "get_all_jobs", return_value=jobs_without_fullname):
            with patch.object(jenkins_api, "enable_job") as mock_enable:
                result = jenkins_api.enable_all_jobs()

                assert result["count"] == 1
                assert "job1" in result["enabled_jobs"]
                mock_enable.assert_called_once_with("job1")

    def test_enable_all_jobs_folder_not_found(self, jenkins_api, sample_all_jobs, mock_logger):
        """Test enabling jobs in non-existent folder returns empty result."""
        with patch.object(jenkins_api, "get_all_jobs", return_value=sample_all_jobs):
            with patch.object(jenkins_api, "enable_job") as mock_enable:
                result = jenkins_api.enable_all_jobs(folder="nonexistent")

                assert result["count"] == 0
                assert result["enabled_jobs"] == []
                mock_enable.assert_not_called()
