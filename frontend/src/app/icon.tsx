import { ImageResponse } from "next/og";

/** High-res so sidebar / tab icons stay sharp when scaled down (retina). */
export const size = { width: 256, height: 256 };
export const contentType = "image/png";

export default function Icon() {
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
          borderRadius: 56,
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 22,
            padding: 36,
            borderRadius: 28,
            background: "#ffffff",
            width: 132,
            height: 168,
            justifyContent: "center",
            boxShadow: "0 8px 24px rgba(15, 23, 42, 0.2)",
          }}
        >
          <div style={{ height: 16, background: "#312e81", borderRadius: 8, width: "100%" }} />
          <div style={{ height: 16, background: "#4f46e5", borderRadius: 8, width: "88%" }} />
          <div style={{ height: 16, background: "#818cf8", borderRadius: 8, width: "70%" }} />
        </div>
      </div>
    ),
    { ...size },
  );
}
