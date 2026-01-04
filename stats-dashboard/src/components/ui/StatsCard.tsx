import { cn } from "@/lib/utils"
import { LucideIcon } from "lucide-react"

interface StatsCardProps {
    title: string
    value: string | number
    icon: LucideIcon
    subtitle?: string
    trend?: string
    delay?: number
}

export function StatsCard({ title, value, icon: Icon, subtitle, trend, delay = 0 }: StatsCardProps) {
    return (
        <div
            className={cn(
                "glass-panel rounded-xl p-4 relative overflow-hidden group cursor-pointer",
                "hover:-translate-y-0.5 transition-transform duration-300"
            )}
            style={{ animationDelay: `${delay}ms` }}
        >
            <div className="flex justify-between items-start mb-3 relative z-10">
                <div className="p-2 rounded-lg bg-white/5 border border-white/10 group-hover:border-primary/50 group-hover:bg-primary/10 transition-colors">
                    <Icon className="w-4 h-4 text-slate-400 group-hover:text-primary transition-colors" />
                </div>
                {trend && (
                    <span className="text-[10px] font-bold text-emerald-400 bg-emerald-400/10 px-1.5 py-0.5 rounded-full border border-emerald-400/20">
                        {trend}
                    </span>
                )}
            </div>

            <div className="relative z-10">
                <h3 className="text-2xl font-bold text-white tracking-tight mb-0.5 tabular-nums">
                    {value}
                </h3>
                <p className="text-xs font-medium text-slate-400 group-hover:text-slate-200 transition-colors">
                    {title}
                </p>
                {subtitle && (
                    <p className="text-[10px] text-slate-500 mt-0.5">{subtitle}</p>
                )}
            </div>
        </div>
    )
}
