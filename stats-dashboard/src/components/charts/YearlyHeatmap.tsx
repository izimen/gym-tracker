import { cn } from "@/lib/utils"

interface YearlyHeatmapProps {
    data: { date: string; hasWorkout: boolean }[]
    year: number
    onYearChange: (year: number) => void
    className?: string
}

const MONTHS = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze", "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

export function YearlyHeatmap({ data, year, onYearChange, className }: YearlyHeatmapProps) {
    // Group data by month
    const monthlyData = MONTHS.map((month, monthIndex) => {
        const monthData = data.filter(d => {
            const date = new Date(d.date)
            return date.getMonth() === monthIndex
        })
        return { month, data: monthData }
    })

    // Calculate Stats
    const totalWorkouts = data.filter(d => d.hasWorkout).length
    const activePercentage = Math.round((totalWorkouts / data.length) * 100) || 0

    // Calculate longest streak
    let maxStreak = 0
    let currentStreak = 0
    const sortedData = [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

    for (const day of sortedData) {
        if (day.hasWorkout) {
            currentStreak++
        } else {
            maxStreak = Math.max(maxStreak, currentStreak)
            currentStreak = 0
        }
    }
    maxStreak = Math.max(maxStreak, currentStreak)

    return (
        <div className={cn("p-6", className)}>
            <div className="flex justify-between items-end mb-6">
                {/* Left Title */}
                <div>
                    <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-widest">Roczna aktywność</h3>
                    <p className="text-[10px] text-zinc-600 font-medium mt-1">Wizualizacja intensywności treningowej</p>
                </div>

                {/* Right Stats & Year - Filling the void */}
                <div className="flex items-center gap-8">
                    <div className="flex gap-6">
                        <div className="text-right">
                            <div className="text-[9px] text-zinc-600 font-bold uppercase tracking-wider mb-0.5">Treningi</div>
                            <div className="text-lg font-black text-white leading-none">{totalWorkouts}</div>
                        </div>
                        <div className="text-right">
                            <div className="text-[9px] text-zinc-600 font-bold uppercase tracking-wider mb-0.5">Aktywność</div>
                            <div className="text-lg font-black text-white leading-none">{activePercentage}%</div>
                        </div>
                        <div className="text-right">
                            <div className="text-[9px] text-zinc-600 font-bold uppercase tracking-wider mb-0.5">Max Seria</div>
                            <div className="text-lg font-black text-emerald-500 leading-none">{maxStreak} <span className="text-[10px] text-emerald-500/60 font-medium">dni</span></div>
                        </div>
                    </div>

                    <div className="h-8 w-px bg-zinc-800" /> {/* Divider */}

                    <div className="text-4xl font-black text-zinc-800 tracking-tighter select-none">
                        {year}
                    </div>
                </div>
            </div>

            <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
                {monthlyData.map((monthObj, monthIndex) => (
                    <div key={monthObj.month} className="flex flex-col gap-2 min-w-max">
                        {/* Month label */}
                        <div className="text-[9px] font-bold text-zinc-600 uppercase tracking-widest text-center">
                            {monthObj.month}
                        </div>

                        {/* Grid */}
                        <div className="grid grid-rows-7 grid-flow-col gap-1">
                            {Array.from({ length: 31 }, (_, dayIndex) => {
                                const day = dayIndex + 1
                                const dateStr = `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                                const dayData = monthObj.data.find(d => d.date === dateStr)
                                const hasWorkout = dayData?.hasWorkout || false
                                const daysInMonth = new Date(year, monthIndex + 1, 0).getDate()

                                if (day > daysInMonth) return <div key={day} className="w-2 h-2" />

                                return (
                                    <div
                                        key={day}
                                        className={cn(
                                            "w-2 h-2 rounded-[1px] transition-all duration-300",
                                            hasWorkout
                                                ? "bg-emerald-500 shadow-[0_0_4px_rgba(16,185,129,0.3)]"
                                                : "bg-zinc-900"
                                        )}
                                        title={`${day} ${monthObj.month}`}
                                    />
                                )
                            }).slice(0, 31)}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
