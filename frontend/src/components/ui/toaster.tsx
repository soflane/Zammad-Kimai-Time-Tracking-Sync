import { Toast, ToastProvider, ToastViewport } from './toast'
import { useToast } from '@/hooks/use-toast'

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider>
      {toasts.map(function (toast) {
        return (
          <Toast key={toast.id} {...toast}>
            <div className="grid gap-1">
              {toast.title && <div className="text-sm font-semibold">{toast.title}</div>}
              {toast.description && (
                <div className="text-sm opacity-90">{toast.description}</div>
              )}
            </div>
            {toast.action}
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
