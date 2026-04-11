import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(145deg, #312e81 0%, #4f46e5 52%, #6366f1 100%)",
          borderRadius: 40,
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 14,
            padding: 26,
            borderRadius: 20,
            background: "#ffffff",
            width: 94,
            height: 118,
            justifyContent: "center",
            boxShadow: "0 6px 18px rgba(15, 23, 42, 0.18)",
          }}
        >
          <div style={{ height: 12, background: "#312e81", borderRadius: 6, width: "100%" }} />
          <div style={{ height: 12, background: "#4f46e5", borderRadius: 6, width: "88%" }} />
          <div style={{ height: 12, background: "#818cf8", borderRadius: 6, width: "70%" }} />
        </div>
      </div>
    ),
    { ...size },
  );
}
