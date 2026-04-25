from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Plain, Video
import aiohttp

from astrbot.api import AstrBotConfig,logger

@register("video_plugin", "anlan", "astrbot_plugin_video", "1.3.0", "https://github.com/01Anlan/astrbot_plugin_video")
class DwoVideoPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        logger.info("測試config",self.config)

        # 支持直接保存配置
        self.config.save_config() # 保存配置


        self.api_urls = {
            "video": "https://api.zhcnli.com/api/sjsp/index.php",
            "hs": "https://api.zhcnli.com/api/hssp/index.php",
            "bs": "https://api.zhcnli.com/api/bs/index.php",
        }
        self.session = aiohttp.ClientSession()


    async def terminate(self):
        await self.session.close()

    @filter.command("video", alias={"小视频", "短视频"})
    async def get_dwo_video(self, event: AstrMessageEvent):
        async for result in self._send_video(event, "video"):
            yield result

    @filter.command("hs")
    async def get_hs_video(self, event: AstrMessageEvent):
        async for result in self._send_video(event, "hs"):
            yield result

    @filter.command("bs")
    async def get_bs_video(self, event: AstrMessageEvent):
        async for result in self._send_video(event, "bs"):
            yield result

    async def _send_video(self, event: AstrMessageEvent, video_type: str):
        try:
            api_url = self.api_urls.get(video_type)
            if not api_url:
                yield event.plain_result("不支持的视频类型")
                return

            params = {
                "ckey": self.config.get("ckey", ""),
                "type": "video"
            }
            headers = {}

            if not params["ckey"]:
                yield event.plain_result("插件未配置 ckey，请先在插件配置中填写 ckey")
                return

            video_url = f"{api_url}?ckey={params['ckey']}&type={params['type']}"

            async with self.session.get(api_url, params=params, headers=headers) as response:
                if response.status != 200:
                    yield event.plain_result(f"请求失败：状态码{response.status}")
                    return
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    context = await response.json()
                    video_url = str(context.get("data", {}).get("url", "")).strip()
                elif "text/" in content_type:
                    context = await response.text()
                else:
                    context = f"<binary content: {content_type or 'unknown'}>"

                logger.info(f"API 响应内容类型：{content_type}")
                logger.info(f"視頻信息：{context}")

                if not video_url:
                    yield event.plain_result("API 未返回有效的视频链接")
                    return

                video_component = Video.fromURL(video_url)
                logger.info(f"視頻組件：{video_component}")

                message_chain = [
                    Plain(f"\u200b视频获取成功！\n视频链接：\u200b{video_url}"),
                    video_component
                ]

                yield event.chain_result(message_chain)

                if self.config.get("debug_mode", False):
                    message_debug_chain = [
                        Plain(f"\u200b\n响应内容类型：{content_type}"),
                        Plain(f"\nAPI 响应内容：{context}\u200b")
                    ]
                    yield event.chain_result(message_debug_chain)

        except aiohttp.ClientError as e:
            yield event.plain_result(f"网络请求出错：{str(e)}")
        except Exception as e:
            yield event.plain_result(f"发生未知错误：{str(e)}")
            import traceback
            traceback.print_exc()
