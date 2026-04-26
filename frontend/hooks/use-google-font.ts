import { useEffect } from "react";

export function useGoogleFont(fontName: string) {
  useEffect(() => {
    if (!fontName || typeof window === "undefined") return;

    const id = `google-font-${fontName.replace(/\s+/g, "-").toLowerCase()}`;
    if (document.getElementById(id)) return;

    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = `https://fonts.googleapis.com/css2?family=${fontName.replace(
      /\s+/g,
      "+",
    )}&display=swap`;

    document.head.appendChild(link);

    return () => {
      const existingLink = document.getElementById(id);
      if (existingLink) {
        document.head.removeChild(existingLink);
      }
    };
  }, [fontName]);
}
