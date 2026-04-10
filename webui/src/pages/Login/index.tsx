import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "antd";
import { useAppMessage } from "../../hooks/useAppMessage";
import { QrcodeOutlined } from "@ant-design/icons";
import { authApi } from "../../api/modules/auth";
import { setAuthToken } from "../../api/config";
import { useTheme } from "../../contexts/ThemeContext";

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isDark } = useTheme();
  const [yukuaiLoading, setYukuaiLoading] = useState(false);
  const { message } = useAppMessage();

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");
    const username = urlParams.get("username");
    if (token && username) {
      setAuthToken(token);
      urlParams.delete("token");
      urlParams.delete("username");
      const redirect = urlParams.toString()
        ? `?${urlParams.toString()}`
        : "/chat";
      message.success(`欢迎回来，${username}`);
      navigate(redirect, { replace: true });
    }
  }, [navigate, message]);

  const handleYukuaiLogin = async () => {
    setYukuaiLoading(true);
    try {
      // Store frontend URL so backend callback can redirect back
      const frontendUrl = window.location.origin;
      localStorage.setItem('copaw_frontend_url', frontendUrl);
      
      const res = await authApi.yukuaiLogin();
      if (res.enabled && res.login_url) {
        window.location.href = res.login_url;
      } else {
        message.warning("渝快政登录未启用");
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "未知错误";
      message.error(`渝快政扫码登录失败，失败信息：${errorMsg}`);
    } finally {
      setYukuaiLoading(false);
    }
  };

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: isDark
          ? "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)"
          : "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
      }}
    >
      <div
        style={{
          width: 400,
          padding: 32,
          borderRadius: 12,
          background: isDark ? "#1f1f1f" : "#fff",
          boxShadow: isDark
            ? "0 4px 24px rgba(0,0,0,0.4)"
            : "0 4px 24px rgba(0,0,0,0.1)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <img
            src={`${import.meta.env.BASE_URL}${
              isDark ? "dark-logo.png" : "logo.png"
            }`}
            alt="GRPClaw"
            style={{ height: 56, marginBottom: 16 }}
          />
          <h2
            style={{
              margin: "0 0 8px",
              fontWeight: 600,
              fontSize: 24,
              color: isDark ? "#fff" : "#000",
            }}
          >
            欢迎使用 GRPClaw
          </h2>
          <p
            style={{
              margin: "0 0 32px",
              color: isDark ? "rgba(255,255,255,0.45)" : "#666",
              fontSize: 14,
            }}
          >
            懂你所需，伴你左右
          </p>
        </div>

        <Button
          type="primary"
          size="large"
          loading={yukuaiLoading}
          icon={<QrcodeOutlined />}
          onClick={handleYukuaiLogin}
          block
          style={{
            height: 48,
            borderRadius: 8,
            fontWeight: 500,
            fontSize: 16,
          }}
        >
          渝快政扫码登录
        </Button>
      </div>
    </div>
  );
}