import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2",
  {
    variants: {
      variant: {
        // App-themed defaults with explicit light/dark colors
        default:
          "border-transparent !bg-teal-600 dark:!bg-teal-500 !text-white hover:!bg-teal-700 dark:hover:!bg-teal-600",
        secondary:
          "border-transparent !bg-slate-100 dark:!bg-slate-800 !text-slate-700 dark:!text-slate-300 hover:!bg-slate-200 dark:hover:!bg-slate-700",
        success:
          "border-transparent !bg-green-100 dark:!bg-green-900/30 !text-green-800 dark:!text-green-200 hover:!bg-green-200 dark:hover:!bg-green-900/50",
        destructive:
          "border-transparent !bg-red-600 dark:!bg-red-500 !text-white hover:!bg-red-700 dark:hover:!bg-red-600",
        outline:
          "!text-slate-700 dark:!text-slate-300 !border-slate-300 dark:!border-slate-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge }
