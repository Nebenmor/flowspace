// Shared helpers for overdue calculations, used by TaskCard and TaskDetailModal
// so the two views can never disagree about what "overdue" means.

export function isOverdue(task) {
  if (!task?.due_date) return false
  if (task.status === 'done' || task.status === 'cancelled') return false
  return new Date(task.due_date) < new Date()
}

export function overdueDays(task) {
  if (!isOverdue(task)) return 0
  const diffMs = new Date() - new Date(task.due_date)
  return Math.max(1, Math.ceil(diffMs / (1000 * 60 * 60 * 24)))
}