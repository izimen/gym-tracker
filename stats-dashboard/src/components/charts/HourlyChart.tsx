import { cn } from "@/lib/utils"

interface HourlyChartProps {
    data: { hour: number; value: number }[]
    className?: string
}

export function HourlyChart({ data, className }: HourlyChartProps) {
    const maxValue = Math.max(...data.map((d) => d.value), 1)

    // Color logic
    const getBarColor = (value: number, max: number) => {
        const ratio = value / max
        if (ratio < 0.35) return "bg-zinc-800" // Low - subtle
        if (ratio < 0.65) return "bg-indigo-900/50 border-t-2 border-indigo-500" // Med - styled
        return "bg-white shadow-[0_0_15px_rgba(255,255,255,0.4)]" // High - BRIGHT
    }

    return (
        <div className={cn("relative h-full pt-6", className)}>
            <div className="flex items-end gap-[2px] h-full">
                {data.map((item, index) => {
                    const height = (item.value / maxValue) * 100
                    const isPeak = item.value > maxValue * 0.85
                    const showLabel = index % 3 === 0 || isPeak // Show less frequent labels to avoid clutter

                    return (
                        <div
                            key={item.hour}
                            className="group flex-1 flex flex-col items-center h-full relative"
                        >
                            {/* Label for Peaks only */}
                            {isPeak && (
                                <div className="absolute -top-6 text-[10px] font-black text-white bg-black/50 px-1 rounded backdrop-blur-sm z-10 border border-white/10">
                                    {item.value}
                                </div>
                            )}

                            {/* Bar */}
                            <div className="flex-1 w-full flex items-end justify-center px-[1px]">
                                <div
                                    className={cn(
                                        "w-full rounded-sm transition-all duration-300",
                                        getBarColor(item.value, maxValue)
                                    )}
                                    style={{ height: `${height}%`, minHeight: '4px' }}
                                />
                            </div>

                            {/* Hour Labels */}
                            {(index % 3 === 0 || index === data.length - 1) && (
                                <div className="absolute -bottom-5 text-[9px] font-bold text-zinc-600">
                                    {item.hour}
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
