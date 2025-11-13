"use client"

import * as React from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface PaginationProps extends React.HTMLAttributes<HTMLElement> {}

function Pagination({ className, ...props }: PaginationProps) {
  return (
    <nav
      role="navigation"
      aria-label="Pagination Navigation"
      className={cn(
        "mx-auto flex w-full justify-center",
        className
      )}
      {...props}
    />
  )
}

Pagination.displayName = "Pagination"

const PaginationContent = React.forwardRef<
  HTMLUListElement,
  React.HTMLAttributes<HTMLUListElement>
>(({ className, ...props }, ref) => (
  <ul
    ref={ref}
    className={cn(
      "flex flex-row items-center gap-1",
      className
    )}
    {...props}
  />
))

PaginationContent.displayName = "PaginationContent"

function PaginationEllipsis({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      aria-hidden
      className={cn(
        "flex h-9 w-9 items-center justify-center",
        className
      )}
      {...props}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="8" cy="12" r="2" />
        <circle cx="12" cy="12" r="2" />
        <circle cx="16" cy="12" r="2" />
      </svg>
    </span>
  )
}

interface PaginationItemProps
  extends React.ComponentPropsWithoutRef<typeof Button> {}

function PaginationItem({ className, ...props }: PaginationItemProps) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn("gap-1 h-9 w-9", className)}
      {...props}
    />
  )
}

PaginationItem.displayName = "PaginationItem"

function PaginationPrevious({ className, ...props }: PaginationItemProps) {
  return (
    <PaginationItem className={className} {...props}>
      <ChevronLeft className="h-4 w-4" />
      <span className="sr-only">Previous</span>
    </PaginationItem>
  )
}

function PaginationNext({ className, ...props }: PaginationItemProps) {
  return (
    <PaginationItem className={className} {...props}>
      <ChevronRight className="h-4 w-4" />
      <span className="sr-only">Next</span>
    </PaginationItem>
  )
}

function PaginationLink({ className, children, ...props }: PaginationItemProps) {
  return (
    <PaginationItem className={className} {...props}>
      <span>{children}</span>
    </PaginationItem>
  )
}

export { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious }
