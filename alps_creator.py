import chainlit as cl
import boto3
from typing import cast, Dict, Any, Optional
from typing import AsyncGenerator
from prompt import SYSTEM_PROMPT  # 추가된 임포트


def load_alps_template():
    """ALPS.md 템플릿 파일을 읽어옵니다."""
    try:
        with open("ALPS.md", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"템플릿 로드 실패: {e}")
        return ""


class BedrockChat:
    def __init__(self):
        self.client = boto3.client("bedrock-runtime")
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.system_prompt = SYSTEM_PROMPT
        self.template = load_alps_template()  # 템플릿 로드
        self.conversation_history = []  # 대화 기록을 저장할 리스트
        self.is_first_message = True  # 첫 메시지 여부를 추적

    async def get_stream_response(self, message: str) -> AsyncGenerator[str, None]:
        """Bedrock Converse API를 사용하여 스트리밍 응답을 생성합니다."""
        try:
            # 새 메시지를 대화 기록에 추가
            self.conversation_history.append(
                {"role": "user", "content": message})

            # 첫 메시지일 때만 템플릿 포함
            if self.is_first_message:
                context = f"{self.system_prompt}\n\n### ALPS 템플릿:\n{
                    self.template}\n\n### 대화 기록:\n{message}"
                self.is_first_message = False
            else:
                # 이후에는 대화 기록만 포함
                conversation = "\n\n".join(
                    [
                        f"{msg['role']}: {msg['content']}"
                        for msg in self.conversation_history
                    ]
                )
                context = f"{self.system_prompt}\n\n### 대화 기록:\n{conversation}"

            response = self.client.converse_stream(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": context}]}],
            )

            # 스트리밍 응답 수신 및 저장
            full_response = ""
            async for chunk in self._process_stream(response):
                full_response += chunk
                yield chunk

            # 어시스턴트의 응답을 대화 기록에 추가
            self.conversation_history.append(
                {"role": "assistant", "content": full_response}
            )

        except Exception as e:
            print(f"Error in get_stream_response: {e}")
            yield f"오류가 발생했습니다: {str(e)}"

    async def _process_stream(self, response):
        """스트리밍 응답을 처리하는 헬퍼 메서드"""
        for event in response["stream"]:
            if "contentBlockDelta" in event:
                if "delta" in event["contentBlockDelta"]:
                    if "text" in event["contentBlockDelta"]["delta"]:
                        yield event["contentBlockDelta"]["delta"]["text"]


class ALPSDocumentCreator:
    def __init__(self):
        self.sections: Dict[str, Any] = {
            "overview": {},
            "goal_metrics": {},
            "requirements_summary": {},
            "high_level_architecture": {},
            "design_specification": {},
            "feature_specification": {},
            "data_model": {},
            "api_spec": {},
            "deployment_operation": {},
            "mvp_metrics": {},
            "out_of_scope": {},
            "appendix": {},
        }
        self.current_section: Optional[str] = None
        self.bedrock_chat = BedrockChat()

    async def handle_section_input(self, section: str, user_input: str) -> None:
        """섹션별 사용자 입력을 처리하고 저장합니다."""
        if section in self.sections:
            self.sections[section] = user_input

            # LLM에 메시지 전송 및 스트리밍 응답 처리
            message = cl.Message(content="")
            await message.send()

            async for chunk in self.bedrock_chat.get_stream_response(user_input):
                await message.stream_token(chunk)

            await message.update()

    async def preview_document(self) -> None:
        """현재 문서 상태를 미리보기로 보여줍니다."""
        preview = "# ALPS Specification Preview\n\n"
        for section, content in self.sections.items():
            if content:
                preview += f"## {section.title()}\n{content}\n\n"

        await cl.Message(content=preview).send()

    async def edit_section(self, section: str, new_content: str) -> None:
        """특정 섹션의 내용을 수정합니다."""
        if section in self.sections:
            self.sections[section] = new_content
            await cl.Message(content=f"{section} 섹션이 수정되었습니다.").send()

    def save_document(self) -> str:
        """문서를 마크다운 형식으로 저장합니다."""
        markdown_content = "# ALPS Specification\n\n"
        for section, content in self.sections.items():
            if content:
                markdown_content += f"## {section.title()}\n{content}\n\n"

        with open("alps_specification.md", "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return "alps_specification.md"


@cl.on_chat_start
async def start():
    """채팅 세션을 시작하고 ALPS 문서 생성기를 초기화합니다."""
    alps_creator = ALPSDocumentCreator()
    cl.user_session.set("alps_creator", alps_creator)
    welcome_message = """
**사용 가능한 명령어:**
- /preview: 현재까지의 문서 미리보기
- /edit [섹션명]: 특정 섹션 수정
- /save: 문서 저장

---

저와 함께 다음 내용들을 함께 작성하게 됩니다:
- overview: 개요
- goal_metrics: MVP 목표와 핵심 지표
- requirements_summary: 요구사항 요약
- high_level_architecture: 전체 아키텍처 개요
- design_specification: 디자인 스펙
- feature_specification: 주요 기능별 설계
- data_model: 데이터 모델/스키마
- api_spec: API 명세
- deployment_operation: 배포 및 운영
- mvp_metrics: MVP 측정 항목
- out_of_scope: 기술적 부채 관리
- appendix: 부록

---

그럼 ALPS 명세서 작성을 시작해볼까요?

먼저 이번 MVP 를 통해 어떤 가설을 실험하고 싶으신지 알려주세요.
""".strip()
    await cl.Message(content=welcome_message).send()


@cl.on_message
async def main(message: cl.Message):
    """사용자 메시지를 처리합니다."""
    alps_creator: ALPSDocumentCreator = cast(
        ALPSDocumentCreator, cl.user_session.get("alps_creator")
    )

    # 명령어 처리
    if message.content.startswith("/"):
        command = message.content[1:].lower()

        if command == "preview":
            await alps_creator.preview_document()

        elif command.startswith("edit"):
            section = command.split()[1]
            await cl.Message(
                content=f"{section} 섹션의 새로운 내용을 입력해주세요."
            ).send()
            alps_creator.current_section = section

        elif command == "save":
            filename = alps_creator.save_document()
            msg = await cl.Message(content=f"문서가 저장되었습니다: {filename}").send()
            await cl.File(path=filename).send(for_id=msg.id)

        return

    # 일반 입력 처리
    if alps_creator.current_section:
        await alps_creator.handle_section_input(
            alps_creator.current_section, message.content
        )
        alps_creator.current_section = None
    else:
        # LLM에 일반 메시지 전송 및 스트리밍 응답 처리
        response_message = cl.Message(content="")
        await response_message.send()

        async for chunk in alps_creator.bedrock_chat.get_stream_response(
            message.content
        ):
            await response_message.stream_token(chunk)

        await response_message.update()
