import logging
from typing import Optional, AsyncGenerator, Any, Dict, List

from app.domain.models.event import BaseEvent, MessageEvent, PlanEvent, PlanEventStatus
from app.domain.models.message import Message
from app.domain.models.plan import Plan, Step
from app.domain.services.prompts.planner import (
    PLANNER_SYSTEM_PROMPT,
    CREATE_PLAN_PROMPT,
    UPDATE_PLAN_PROMPT,
)
from app.domain.services.prompts.system import SYSTEM_PROMPT
from .base import BaseAgent

"""
多Agent系统/flow=PlannerAgent+ReActAgent

顺序:
1. PlannerAgent生成规划;
2. 循环取出规划中的子步骤，让ReActAgent执行，依次迭代;
3. ReActAgent执行完每一个子步骤之后，需要将子步骤结果+Plan传递给PlannerAgent让其更新计划/Plan；
4. 循环取出规划中的子步骤，让ReActAgent执行，依次迭代;
5. ...
6. 直到所有子任务/步骤都完成，这时候将子步骤的所有结果汇总进行总结(ReActAgent);

PlannerAgent:
- 功能: 将用户的需求拆解成多个子任务+根据已完成的子任务更新规划
- 提示词: 创建规划的prompt、更新规划的prompt

ReActAgent:
- 功能: 迭代执行完每一个子任务、汇总所有的子任务进行总结
- 提示词: 执行任务的prompt、汇总总结prompt
"""

logger = logging.getLogger(__name__)


def _normalize_steps(data: Dict[str, Any]) -> Dict[str, Any]:
    """规范化 steps 数据格式，处理 AI 返回字符串列表的情况

    有些 AI 模型可能返回 steps: ["b10", "b11"] 这样的字符串列表，
    而不是标准的 [{"id": "b10", "description": "..."}, ...] 对象列表。
    此函数会自动将字符串列表转换为对象列表。
    """
    if "steps" not in data:
        return data

    steps = data["steps"]
    if not isinstance(steps, list):
        return data

    normalized_steps: List[Dict[str, Any]] = []
    for step in steps:
        if isinstance(step, str):
            # 将字符串转换为标准对象格式
            normalized_steps.append({"id": step, "description": ""})
        elif isinstance(step, dict):
            # 确保对象包含必要的字段
            normalized_step = {
                "id": step.get("id", ""),
                "description": step.get("description", ""),
            }
            normalized_steps.append(normalized_step)
        else:
            # 其他类型，尝试转换为字符串作为 id
            normalized_steps.append({"id": str(step), "description": ""})

    data["steps"] = normalized_steps
    return data


class PlannerAgent(BaseAgent):
    """规划Agent，用于将用户的任务/需求拆解成多个子步骤"""
    name: str = "planner"
    _system_prompt: str = SYSTEM_PROMPT + PLANNER_SYSTEM_PROMPT
    _format: Optional[str] = "json_object"
    _tool_choice: Optional[str] = "none"

    async def create_plan(self, message: Message) -> AsyncGenerator[BaseEvent, None]:
        """根据用户传递的消息创建计划/规划，迭代返回对应的事件"""
        # 1.根据用户传递的消息生成创建plan的提示词
        query = CREATE_PLAN_PROMPT.format(
            message=message.message,
            attachments="\n".join(message.attachments),
        )

        # 2.调用invoke函数返回迭代事件
        async for event in self.invoke(query):
            # 3.规划智能体因为使用json_object，正常情况下会返回MessageEvent
            if isinstance(event, MessageEvent):
                # 4.记录日志并使用json解析器解析得到对应的数据
                logger.info(f"PlannerAgent生成消息: {event.message}")
                parsed_obj = await self._json_parser.invoke(event.message)

                # 5.规范化 steps 数据格式（处理 AI 返回字符串列表的情况）
                normalized_obj = _normalize_steps(parsed_obj)

                # 6.将解析对象转换成Plan计划
                plan = Plan.model_validate(normalized_obj)

                # 7.返回PlanEvent表示规划创建成功
                yield PlanEvent(plan=plan, status=PlanEventStatus.CREATED)
            else:
                # 返回不是消息事件的事件
                yield event

    async def update_plan(self, plan: Plan, step: Step) -> AsyncGenerator[BaseEvent, None]:
        """根据传递的原始规划+子步骤更新事件"""
        # 1.使用plan+step创建更新Plan提示词
        query = UPDATE_PLAN_PROMPT.format(
            plan=plan.model_dump_json(),
            step=step.model_dump_json(),
        )

        # 2.调用invoke获取对应的事件
        async for event in self.invoke(query):
            # 3.判断规划Agent生成的事件是不是消息事件
            if isinstance(event, MessageEvent):
                # 4.记录日志并解析json
                logger.info(f"PlannerAgent生成消息: {event.message}")
                parsed_obj = await self._json_parser.invoke(event.message)

                # 5.规范化 steps 数据格式（处理 AI 返回字符串列表的情况）
                normalized_obj = _normalize_steps(parsed_obj)

                # 6.将解析对象转换成Plan
                updated_plan = Plan.model_validate(normalized_obj)

                # 7.拷贝更新计划中的steps，避免造成数据污染
                new_steps = [Step.model_validate(step) for step in updated_plan.steps]

                # 8.查询旧计划中第一个未完成的计划
                first_pending_index = None
                for idx, step in enumerate(plan.steps):
                    if not step.done:
                        first_pending_index = idx
                        break

                # 9.判断是否有未完成的步骤，如果有则执行更新
                if first_pending_index is not None:
                    # 10.获取历史已完成的子步骤并更新
                    updated_steps = plan.steps[:first_pending_index]
                    updated_steps.extend(new_steps)

                    # 11.更新plan规划
                    plan.steps = updated_steps

                # 12.返回规划更新事件
                yield PlanEvent(plan=plan, status=PlanEventStatus.UPDATED)
            else:
                # 其他事件则直接返回
                yield event