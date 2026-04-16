"""YAML-driven refine crew (first_crew / CrewBase style)."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.llm import LLM
from crewai.project import CrewBase, agent, crew, task

from app.crewai_mcp_support import build_mcp_servers, model_name


@CrewBase
class InterviewRefineCrew:
    """Coaches a single interview answer with feedback and a refined version."""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def answer_coach(self) -> Agent:
        return Agent(
            config=self.agents_config["answer_coach"],  # type: ignore[index]
            verbose=True,
            # llm=LLM(model=model_name()),
            mcps=build_mcp_servers(),
        )

    @task
    def refine_answer_task(self) -> Task:
        return Task(
            config=self.tasks_config["refine_answer_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tracing=True
        )
