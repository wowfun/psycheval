import sys

import pytest

from psycheval.harbor.acp_agent import HostACPAgent
from psycheval.harbor.hermes import HermesAgent
from psycheval.harbor.workbuddy_agent import HostWorkBuddyAgent


def test_acp_skill_admission_follows_subclass_capabilities(tmp_path):
    class SkillAgent(HostACPAgent):
        capabilities = HostACPAgent.capabilities.model_copy(update={"skills": True})

    skills = tmp_path / "skills"
    skills.mkdir()
    agent = SkillAgent(logs_dir=tmp_path, argv=[sys.executable], skills_dir=skills)
    assert agent.skills_dir == skills
    with pytest.raises(ValueError, match="does not support Skills"):
        HostACPAgent(logs_dir=tmp_path, argv=[sys.executable], skills_dir=skills)

    assert HostWorkBuddyAgent.capabilities.skills

    class NoSkillAgent(SkillAgent):
        capabilities = SkillAgent.capabilities.model_copy(update={"skills": False})

    with pytest.raises(ValueError, match="does not support Skills"):
        NoSkillAgent(logs_dir=tmp_path, argv=[sys.executable], skills_dir=skills)


def test_hermes_declares_its_effective_upstream_and_resume_capabilities():
    capabilities = HermesAgent.capabilities
    assert capabilities.atif and capabilities.skills and capabilities.mcp_servers
    assert capabilities.resume
    assert not capabilities.load_native_trajectory
    assert not capabilities.load_atif_trajectory
