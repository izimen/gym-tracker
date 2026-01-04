import { cn } from "@/lib/utils"
import { ArrowUp, ArrowDown, Minus } from "lucide-react"

interface MonthComparisonProps {
    prevMonth: {
        name: string
        count: number
    }
    currMonth: {
        name: string
        count: number
    }
    className?: string
}

export function MonthComparison({ prevMonth, currMonth, className }: MonthComparisonProps) {
    const difference = currMonth.count - prevMonth.count
    const percentChange = prevMonth.count > 0
        ? Math.round((difference / prevMonth.count) * 100)
        : 0

    const changeType = difference > 0 ? "up" : difference < 0 ? "down" : "neutral"

    return (
        <div className={cn("grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-3 items-center", className)}>
            {/* Previous Month */}
            <div className="bg-slate-800/50 rounded-xl p-4 text-center border border-white/5 relative group">
                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                    {prevMonth.name}
                </div>
                <div className="text-2xl font-bold text-slate-300 tabular-nums">
                    {prevMonth.count}
                </div>
                <div className="text-[9px] text-slate-500 mt-1 font-medium">treningów</div>
            </div>

            {/* Change indicator */}
            <div className="flex justify-center">
                <div
                    className={cn(
                        "flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg font-bold text-xs shadow-lg backdrop-blur-sm transition-all duration-300",
                        changeType === "up" && "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-emerald-900/20",
                        changeType === "down" && "bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-rose-900/20",
                        changeType === "neutral" && "bg-slate-800 text-slate-400 border border-slate-700"
                    )}
                >
                    {changeType === "up" && <ArrowUp className="w-3 h-3" />}
                    {changeType === "down" && <ArrowDown className="w-3 h-3" />}
                    {changeType === "neutral" && <Minus className="w-3 h-3" />}
                    <span className="tabular-nums font-mono text-sm">
                        {changeType === "up" && "+"}
                        {percentChange}%
                    </span>
                </div>
            </div>

            {/* Current Month */}
            <div className="bg-gradient-to-br from-primary/20 to-primary/5 rounded-xl p-4 text-center border border-primary/20 relative overflow-hidden group">
                <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="text-[10px] font-bold text-primary/80 uppercase tracking-wider mb-1 relative z-10">
                    {currMonth.name}
                </div>
                <div className="text-2xl font-bold text-white tabular-nums relative z-10">
                    {currMonth.count}
                </div>
                <div className="text-[9px] text-primary/60 mt-1 font-medium relative z-10">treningów</div>
            </div>
        </div>
    )
}
