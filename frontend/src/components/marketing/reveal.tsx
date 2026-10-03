"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export function Reveal({
  children,
  className,
  delay = 0,
  style,
  ...props
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "children">) {
  const element = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [enhanced, setEnhanced] = useState(false);

  useEffect(() => {
    const node = element.current;
    if (!node) return;
    queueMicrotask(() => setEnhanced(true));
    const bounds = node.getBoundingClientRect();
    if (bounds.top < window.innerHeight && bounds.bottom > 0) {
      queueMicrotask(() => setVisible(true));
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={element}
      className={cn("landing-reveal", enhanced && !visible && "is-pending", visible && "is-visible", className)}
      style={{
        ...style,
        "--reveal-delay": `${delay}ms`,
      } as React.CSSProperties}
      {...props}
    >
      {children}
    </div>
  );
}
