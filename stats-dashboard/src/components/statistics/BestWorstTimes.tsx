import { cn } from "@/lib/utils"
import { Trophy, AlertTriangle } from "lucide-react"

interface TimeSlot {
    time: string
    count: number
}

interface BestWorstTimesProps {
    bestTimes: TimeSlot[]
    worstTimes: TimeSlot[]
    className?: string
}

export function BestWorstTimes({ bestTimes, worstTimes, className }: BestWorstTimesProps) {
    return (
        <div className={cn("grid grid-cols-2 gap-4 h-full p-4 relative z-10", className)}>
            {/* Best Times - Emerald Glow */}
            <div className="flex flex-col justify-center">
                <div className="flex items-center gap-2 mb-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                    <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-widest">
                        Najlepsze
                    </h3>
                </div>

                <div className="space-y-2">
                    {bestTimes.map((slot, index) => (
                        <div key={index} className="flex justify-between items-center group">
                            <span className="text-sm font-medium text-zinc-400 group-hover:text-white transition-colors">{slot.time}</span>
                            <span className="text-xs font-bold text-emerald-500">{slot.count} os.</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Worst Times - Rose Glow */}
            <div className="flex flex-col justify-center border-l border-white/5 pl-4">
                <div className="flex items-center gap-2 mb-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]" />
                    <h3 className="text-xs font-bold text-rose-400 uppercase tracking-widest">
                        Unikaj
                    </h3>
                </div>

                <div className="space-y-2">
                    {worstTimes.map((slot, index) => (
                        <div key={index} className="flex justify-between items-center group">
                            <span className="text-sm font-medium text-zinc-400 group-hover:text-white transition-colors">{slot.time}</span>
                            <span className="text-xs font-bold text-rose-500">{slot.count} os.</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
