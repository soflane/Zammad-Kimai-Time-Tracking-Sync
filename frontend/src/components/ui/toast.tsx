import * as React from 'react'

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>
}

export const ToastViewport = () => {
  return (
    <div className="fixed top-0 right-0 z-50 flex max-h-screen w-full flex-col-reverse p-4 sm:top-auto sm:right-0 sm:bottom-0 sm:flex-col md:max-w-[420px]" />
  )
}

interface ToastProps {
  id: string
  title?: string
  description?: string
  action?: React.ReactNode
  variant?: 'default' | 'destructive'
  children?: React.ReactNode
}

export const Toast = ({ variant = 'default', children }: ToastProps) => {
  const variantStyles = variant === 'destructive'
    ? 'bg-red-600 text-white'
    : 'bg-white border border-gray-200'

  return (
    <div className={`group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md p-6 pr-8 shadow-lg transition-all ${variantStyles}`}>
      {children}
    </div>
  )
}
