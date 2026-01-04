import { cn } from "@/lib/utils"
import { TrendingUp, Calendar, Trophy, Sparkles, ArrowRight } from "lucide-react"

interface NewYearEffectProps {
    mainChange: string
    weekdayComparison: string
    peakDay: string
    weeklyTrend?: string
    className?: string
}

export function NewYearEffect({
    mainChange,
    weekdayComparison,
    peakDay,
    weeklyTrend,
    className
}: NewYearEffectProps) {
    return (
        <div
            className={cn(
                "relative rounded-3xl p-6 flex flex-col justify-between overflow-hidden group hover:border-indigo-500/50 transition-colors duration-500",
                "bg-neutral-900/40 border border-white/5", // Base glass
                className
            )}
        >
            {/* Background Gradient */}
            <div className="absolute inset-0 bg-gradient-to-tr from-indigo-600/10 via-transparent to-purple-600/5 opacity-50 group-hover:opacity-100 transition-opacity" />

            {/* Header */}
            <div className="relative z-10 flex items-center gap-3 mb-4">
                <div className="p-2 bg-indigo-500 rounded-lg shadow-[0_0_15px_rgba(99,102,241,0.5)]">
                    <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h3 className="text-lg font-black text-white tracking-tight">
                        Raport Q1 2026
                    </h3>
                    <p className="text-xs text-indigo-200 font-medium">Analiza trendu noworocznego</p>
                </div>
            </div>

            {/* Stats Main */}
            <div className="relative z-10 grid grid-cols-2 gap-4 mb-4">
                <div className="bg-black/40 rounded-xl p-3 border border-white/5">
                    <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Wzrost globalny</span>
                    <div className="text-2xl font-black text-white mt-1 tabular-nums">{mainChange}</div>
                </div>
                <div className="bg-black/40 rounded-xl p-3 border border-white/5">
                    <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Szczyt (Dzień)</span>
                    <div className="text-sm font-bold text-white mt-2">{peakDay}</div>
                </div>
            </div>

            {/* Forecast Text */}
            <div className="relative z-10 pt-4 border-t border-white/5">
                <div className="flex items-start gap-2">
                    <ArrowRight className="w-4 h-4 text-indigo-500 mt-0.5 shrink-0" />
                    <p className="text-xs text-zinc-400 font-medium leading-relaxed">
                        {weeklyTrend}
                    </p>
                </div>
            </div>
        </div>
    )
}
