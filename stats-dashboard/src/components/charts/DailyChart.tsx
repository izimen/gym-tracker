import { cn } from "@/lib/utils"

interface DailyChartProps {
    data: { day: string; value: number }[]
    className?: string
}

export function DailyChart({ data, className }: DailyChartProps) {
    const maxValue = Math.max(...data.map((d) => d.value), 1)

    return (
        <div className={cn("grid grid-cols-7 gap-2 h-full items-end", className)}>
            {data.map((item, index) => {
                const height = (item.value / maxValue) * 100
                const isMax = item.value === maxValue

                return (
                    <div
                        key={item.day}
                        className="group flex flex-col items-center justify-end h-full relative"
                    >
                        {/* BIG Number Label - Always Visible */}
                        <span className={cn(
                            "font-black text-sm mb-1.5 tabular-nums transition-colors duration-300",
                            isMax ? "text-white scale-110" : "text-zinc-500 group-hover:text-zinc-300"
                        )}>
                            {item.value}
                        </span>

                        {/* Bar */}
                        <div className="w-full h-full flex items-end">
                            <div
                                className={cn(
                                    "w-full rounded-md transition-all duration-500 relative min-h-[4px]",
                                    isMax
                                        ? "bg-white shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                                        : "bg-zinc-800 group-hover:bg-zinc-700"
                                )}
                                style={{ height: `${height}%` }}
                            />
                        </div>

                        {/* Day Label */}
                        <span className={cn(
                            "text-[10px] font-bold uppercase mt-2 tracking-widest",
                            isMax ? "text-white" : "text-zinc-600 group-hover:text-zinc-400"
                        )}>
                            {item.day}
                        </span>
                    </div>
                )
            })}
        </div>
    )
}
