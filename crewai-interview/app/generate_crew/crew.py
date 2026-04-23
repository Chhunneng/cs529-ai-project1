"""YAML-driven generate crew (first_crew / CrewBase style)."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.llm import LLM
from crewai.project import CrewBase, agent, crew, task, llm

from app.crewai_mcp_support import build_mcp_servers, model_name


@CrewBase
class InterviewGenerateCrew:
    """Generates interview questions + sample answers from JD/resume context."""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def question_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["question_generator"],  # type: ignore[index]
            verbose=True,
            # llm=LLM(model=model_name()),
            mcps=build_mcp_servers(),
        )
    
    @agent
    def sample_answer_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["sample_answer_generator"],  # type: ignore[index]
            verbose=True,
            # llm=LLM(model=model_name()),
            mcps=build_mcp_servers(),
        )

    @task
    def generate_questions_task(self) -> Task:
        return Task(
            config=self.tasks_config["generate_questions_task"],  # type: ignore[index]
        )
    
    @task
    def generate_sample_answers_task(self) -> Task:
        return Task(
            config=self.tasks_config["generate_sample_answers_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tracing=True,
        )
