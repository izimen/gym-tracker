import { cn } from "@/lib/utils"

interface WeeklyChartProps {
    data: { week: string; count: number }[]
    className?: string
}

export function WeeklyChart({ data, className }: WeeklyChartProps) {
    const maxCount = Math.max(...data.map((d) => d.count), 1)

    return (
        <div className={cn("flex items-end gap-2 h-full pb-1", className)}>
            {data.map((item, index) => {
                const height = (item.count / maxCount) * 100
                const isLatest = index === data.length - 1

                return (
                    <div
                        key={item.week}
                        className="group flex-1 flex flex-col items-center h-full relative"
                    >
                        {/* Value - Visible ! */}
                        <span className={cn(
                            "text-[10px] font-bold mb-1 transition-colors tabular-nums",
                            isLatest ? "text-amber-400" : "text-zinc-600 group-hover:text-zinc-400"
                        )}>
                            {item.count}
                        </span>

                        {/* Bar */}
                        <div className="flex-1 w-full flex items-end justify-center relative">
                            <div
                                className={cn(
                                    "w-full rounded-sm transition-all duration-300 cursor-pointer",
                                    isLatest
                                        ? "bg-amber-400 shadow-[0_0_15px_rgba(251,191,36,0.5)]"
                                        : "bg-zinc-800 hover:bg-zinc-700"
                                )}
                                style={{ height: `${height}%`, minHeight: '2px' }}
                            />
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
