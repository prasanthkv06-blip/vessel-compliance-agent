interface Props {
  level: 'Low' | 'Medium' | 'High' | 'None' | string
  label?: string
  size?: 'sm' | 'lg'
}

export default function RiskBadge({ level, label, size = 'sm' }: Props) {
  const colors: Record<string, string> = {
    Low: 'bg-green-100 text-green-800',
    None: 'bg-gray-100 text-gray-600',
    Medium: 'bg-yellow-100 text-yellow-800',
    High: 'bg-red-100 text-red-800',
    'Not Sanctioned': 'bg-green-100 text-green-800',
    Sanctioned: 'bg-red-100 text-red-800',
  }

  const sizeClasses = size === 'lg' ? 'px-4 py-2 text-sm' : 'px-2.5 py-0.5 text-xs'

  return (
    <span className={`inline-flex items-center rounded-full font-semibold ${sizeClasses} ${colors[level] || colors['None']}`}>
      {label || level}
    </span>
  )
}
