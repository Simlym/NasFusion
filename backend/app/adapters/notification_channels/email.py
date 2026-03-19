# -*- coding: utf-8 -*-
"""
Email (SMTP) 通知渠道适配器
"""
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from app.adapters.notification_channels.base import BaseNotificationChannel
from app.constants import NOTIFICATION_CHANNEL_EMAIL


class EmailNotificationChannel(BaseNotificationChannel):
    """
    Email (SMTP) 通知渠道

    配置示例:
    {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "your-email@gmail.com",
        "smtp_password": "your-app-password",
        "from_name": "NasFusion",
        "from_email": "noreply@nasfusion.com",
        "to_email": "user@example.com",
        "use_tls": true,
        "use_ssl": false
    }
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validate_config(
            ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "to_email"]
        )

        self.smtp_host = self.get_config_value("smtp_host")
        self.smtp_port = self.get_config_value("smtp_port")
        self.smtp_user = self.get_config_value("smtp_user")
        self.smtp_password = self.get_config_value("smtp_password")
        self.from_name = self.get_config_value("from_name", "NasFusion")
        self.from_email = self.get_config_value("from_email", self.smtp_user)
        self.to_email = self.get_config_value("to_email")
        self.use_tls = self.get_config_value("use_tls", True)
        self.use_ssl = self.get_config_value("use_ssl", False)

    @property
    def channel_type(self) -> str:
        return NOTIFICATION_CHANNEL_EMAIL

    @property
    def supports_html(self) -> bool:
        return True

    @property
    def max_message_length(self) -> int:
        return 100000  # Email 没有严格限制，设置一个较大值

    async def send(
        self,
        title: str,
        content: str,
        priority: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        发送 Email 通知

        Args:
            title: 邮件主题
            content: 邮件内容
            priority: 优先级（Email 支持通过 X-Priority 头设置）
            **kwargs: 额外参数

        Returns:
            发送结果
        """
        try:
            # 创建邮件消息
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = self.to_email

            # 设置优先级
            if priority == "urgent":
                msg["X-Priority"] = "1"
                msg["Importance"] = "High"
            elif priority == "high":
                msg["X-Priority"] = "2"
                msg["Importance"] = "High"

            # 添加纯文本版本
            text_part = MIMEText(content, "plain", "utf-8")
            msg.attach(text_part)

            # 添加 HTML 版本（将换行转换为 <br>）
            html_content = content.replace("\n", "<br>")
            html_body = f"""
            <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                        .content {{ padding: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="content">
                        {html_content}
                    </div>
                </body>
            </html>
            """
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

            # 发送邮件
            if self.use_ssl:
                # 使用 SSL (通常是端口 465)
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                # 使用明文或 STARTTLS (通常是端口 25 或 587)
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)

                if self.use_tls:
                    server.starttls()

            # 登录
            server.login(self.smtp_user, self.smtp_password)

            # 发送
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email 发送成功: to={self.to_email}, subject={title}")

            return {
                "success": True,
                "message": "Email 发送成功",
                "response_data": {
                    "to": self.to_email,
                    "subject": title,
                },
            }

        except smtplib.SMTPAuthenticationError as e:
            error_msg = "SMTP 认证失败，请检查用户名和密码"
            self.logger.error(f"{error_msg}: {str(e)}")
            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
            }

        except smtplib.SMTPConnectError as e:
            error_msg = "无法连接到 SMTP 服务器"
            self.logger.error(f"{error_msg}: {str(e)}")
            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
            }

        except smtplib.SMTPException as e:
            error_msg = f"SMTP 错误: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
            }

        except Exception as e:
            error_msg = f"Email 发送异常: {str(e)}"
            self.logger.exception(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
            }

    async def test_connection(self) -> Dict[str, Any]:
        """
        测试 SMTP 连接

        尝试连接并登录 SMTP 服务器
        """
        try:
            start_time = time.time()

            # 连接
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)

                if self.use_tls:
                    server.starttls()

            # 登录测试
            server.login(self.smtp_user, self.smtp_password)
            server.quit()

            latency_ms = int((time.time() - start_time) * 1000)

            self.logger.info(
                f"SMTP 连接测试成功: {self.smtp_host}:{self.smtp_port}, latency={latency_ms}ms"
            )

            return {
                "success": True,
                "message": f"连接成功! SMTP: {self.smtp_host}:{self.smtp_port}",
                "latency_ms": latency_ms,
            }

        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "message": "认证失败，请检查用户名和密码",
                "latency_ms": 0,
            }

        except smtplib.SMTPConnectError:
            return {
                "success": False,
                "message": f"无法连接到 {self.smtp_host}:{self.smtp_port}",
                "latency_ms": 0,
            }

        except TimeoutError:
            return {
                "success": False,
                "message": "连接超时",
                "latency_ms": 10000,
            }

        except Exception as e:
            self.logger.exception(f"SMTP 连接测试异常: {str(e)}")
            return {
                "success": False,
                "message": f"测试异常: {str(e)}",
                "latency_ms": 0,
            }
