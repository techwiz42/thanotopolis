// src/components/ui/link.tsx
import * as React from "react"
import Link from "next/link"

export interface LinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  href: string
}

const UILink = React.forwardRef<HTMLAnchorElement, LinkProps>(
  ({ className, href, ...props }, ref) => {
    return (
      <Link
        href={href}
        className={`text-primary underline-offset-4 hover:underline ${className}`}
        ref={ref}
        {...props}
      />
    )
  }
)
UILink.displayName = "Link"

export { UILink as Link }
