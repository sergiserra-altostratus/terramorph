"use client";

import { forwardRef } from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Visual variant */
  variant?: "default" | "interactive" | "elevated";
  /** Remove padding (for custom content like code editors) */
  noPadding?: boolean;
}

/**
 * Reusable Card component that unifies border/background/padding/radius styles
 * across the application.
 */
const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant = "default", noPadding = false, className = "", children, ...props }, ref) => {
    const base = "rounded-md border transition-all duration-150";

    const variants = {
      default:
        "border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02]",
      interactive:
        "border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] hover:border-gray-300 dark:hover:border-white/[0.12] hover:shadow-sm cursor-pointer",
      elevated:
        "border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.03] shadow-sm",
    };

    const padding = noPadding ? "" : "p-5";

    return (
      <div
        ref={ref}
        className={`${base} ${variants[variant]} ${padding} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

/** Card header with title and optional action */
function CardHeader({
  title,
  action,
  className = "",
}: {
  title: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex items-center justify-between mb-4 ${className}`}>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      {action}
    </div>
  );
}

/** Card section with top border separator */
function CardSection({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`pt-4 mt-4 border-t border-gray-100 dark:border-white/[0.04] ${className}`}>
      {children}
    </div>
  );
}

export { Card, CardHeader, CardSection };
export default Card;
