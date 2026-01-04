import { useState } from "react"
import { Card } from "@/components/ui/Card"
import { FloatingDock } from "@/components/layout/FloatingDock"
import { DailyChart } from "@/components/charts/DailyChart"
import { HourlyChart } from "@/components/charts/HourlyChart"
import { WeeklyChart } from "@/components/charts/WeeklyChart"
import { YearlyHeatmap } from "@/components/charts/YearlyHeatmap"
import { BestWorstTimes } from "@/components/statistics/BestWorstTimes"
import { NewYearEffect } from "@/components/statistics/NewYearEffect"
import { MonthComparison } from "@/components/statistics/MonthComparison"
import {
    Users,
    TrendingUp,
    Activity,
    Zap
} from "lucide-react"

// Mock Data (same as before)
const mockData = {
    liveCount: 142,
    liveStats: {
        avgWeekday: { value: 312, label: "Śr. dzienna" },
        avgWeekdayHour: { value: 135, label: "Śr. ta godz." },
        avgHour: { value: 128, label: "Śr. ogólnie" },
        liveNow: { value: 142, label: "LIVE" },
    },
    dailyAverages: [
        { day: "Pon", value: 312 }, { day: "Wt", value: 354 }, { day: "Śr", value: 174 },
        { day: "Czw", value: 236 }, { day: "Pt", value: 253 }, { day: "Sob", value: 213 },
        { day: "Nd", value: 141 },
    ],
    hourlyAverages: Array.from({ length: 18 }, (_, i) => ({
        hour: i + 6,
        value: Math.floor(Math.random() * 40) + 10
    })),
    bestTimes: [
        { time: "Śr 21:00", count: 7 },
        { time: "Śr 6:00", count: 9 },
        { time: "Czw 7:00", count: 11 },
    ],
    worstTimes: [
        { time: "Pon 18:00", count: 88 },
        { time: "Pon 17:00", count: 85 },
        { time: "Pon 16:00", count: 78 },
    ],
    weeklyWorkouts: Array.from({ length: 12 }, (_, i) => ({
        week: `W${i + 1}`,
        count: Math.floor(Math.random() * 3) + 3
    })),
    monthComparison: {
        prev: { name: "Lis", count: 18 },
        curr: { name: "Gru", count: 22 },
    },
    heatmapData: generateHeatmapData(2025),
}
mockData.hourlyAverages[12].value = 52; mockData.hourlyAverages[13].value = 48;

function generateHeatmapData(year: number) {
    const data: { date: string; hasWorkout: boolean }[] = []
    const startDate = new Date(year, 0, 1)
    const endDate = new Date(year, 11, 31)
    for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
        data.push({ date: d.toISOString().split('T')[0], hasWorkout: Math.random() > 0.6 })
    }
    return data
}

export function StatisticsPage() {
    const [activeTab, setActiveTab] = useState("stats")
    const [heatmapYear, setHeatmapYear] = useState(2025)

    return (
        <div className="min-h-screen bg-black text-white relative selection:bg-primary/30">

            {/* Background Ambient Glows */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden">
                <div className="absolute -top-[20%] -right-[10%] w-[1000px] h-[1000px] bg-indigo-600/10 rounded-full blur-[150px] opacity-40 animate-pulse" style={{ animationDuration: '8s' }} />
                <div className="absolute -bottom-[20%] -left-[10%] w-[800px] h-[800px] bg-purple-600/10 rounded-full blur-[150px] opacity-30 animate-pulse" style={{ animationDuration: '10s' }} />
            </div>

            <div className="bento-grid relative z-10">
                {/* HERO HEADER - Full Width */}
                <div className="col-span-1 md:col-span-4 lg:col-span-6 flex justify-between items-end mb-4 px-2">
                    <div>
                        <h1 className="text-4xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-500">
                            Dashboard
                        </h1>
                        <p className="text-slate-500 font-medium tracking-tight">System monitorowania obłożenia</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="relative flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                        </span>
                        <span className="font-mono text-emerald-400 font-bold">LIVE</span>
                    </div>
                </div>

                {/* 1. BIG LIVE STATUS - 2x2 Square */}
                <Card className="col-span-1 md:col-span-2 lg:col-span-2 row-span-2 flex flex-col justify-between relative overflow-hidden group border-0 bg-neutral-900/50">
                    <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/20 via-purple-500/5 to-transparent opacity-100 transition-opacity" />

                    <div className="relative z-10 p-2">
                        <div className="flex justify-between items-start">
                            <div className="p-3 bg-white/5 rounded-2xl backdrop-blur-md border border-white/10">
                                <Users className="w-6 h-6 text-white" />
                            </div>
                            <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
                                <span className="text-xs font-bold text-white uppercase tracking-wider">Teraz</span>
                            </div>
                        </div>
                    </div>

                    <div className="relative z-10 text-center py-8">
                        <div className="text-8xl font-black text-white tracking-tighter drop-shadow-2xl">
                            {mockData.liveCount}
                        </div>
                        <p className="text-lg text-indigo-200/60 font-medium mt-[-10px]">osób na siłowni</p>
                    </div>

                    {/* Abstract Decoration */}
                    <div className="absolute -bottom-10 -right-10 w-48 h-48 bg-indigo-500/20 blur-[60px] rounded-full group-hover:bg-indigo-500/30 transition-colors duration-700" />
                </Card>

                {/* 2. HOURLY CHART - 4x2 Wide */}
                <Card className="col-span-1 md:col-span-2 lg:col-span-4 row-span-2 flex flex-col justify-between bg-neutral-900/30">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 bg-white/5 rounded-xl">
                            <Activity className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white leading-none">Aktywność Dobowa</h3>
                            <p className="text-xs text-slate-500 mt-1">Dzisiejsza estymacja</p>
                        </div>
                    </div>
                    <div className="flex-1">
                        <HourlyChart data={mockData.hourlyAverages} />
                    </div>
                </Card>

                {/* 3. QUICK STATS - 1x1 Blocks */}
                <Card className="col-span-1 lg:col-span-1 flex flex-col justify-center items-center bg-neutral-900/20 group hover:bg-neutral-800/40 transition-colors">
                    <p className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-1">Średnia</p>
                    <div className="text-3xl font-bold text-white group-hover:scale-110 transition-transform">{mockData.liveStats.avgWeekday.value}</div>
                    <span className="text-[10px] text-emerald-400 font-bold mt-1 bg-emerald-500/10 px-2 py-0.5 rounded-full">+12%</span>
                </Card>

                <Card className="col-span-1 lg:col-span-1 flex flex-col justify-center items-center bg-neutral-900/20 group hover:bg-neutral-800/40 transition-colors">
                    <p className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-1">Max Dziś</p>
                    <div className="text-3xl font-bold text-white group-hover:scale-110 transition-transform">184</div>
                    <span className="text-[10px] text-slate-500 mt-1">o godz 19:00</span>
                </Card>

                {/* 4. WEEKLY CHART - 2x1 Wide */}
                <Card className="col-span-1 md:col-span-2 lg:col-span-2 bg-neutral-900/30">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-sm font-bold text-slate-300">Ten Tydzień</h3>
                        <TrendingUp className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div className="h-24">
                        <DailyChart data={mockData.dailyAverages} />
                    </div>
                </Card>

                {/* 5. NEW YEAR EFFECT - 2x2 Square */}
                <div className="col-span-1 md:col-span-2 lg:col-span-2 row-span-2">
                    <NewYearEffect
                        mainChange="+145%"
                        weekdayComparison="+85%"
                        peakDay="6 Sty"
                        weeklyTrend="Spadek -20% oczekiwany."
                        className="h-full bg-gradient-to-b from-indigo-900/20 to-black border-indigo-500/20"
                    />
                </div>

                {/* 6. BEST/WORST TIMES - 2x1 Wide */}
                <Card className="col-span-1 md:col-span-2 lg:col-span-2 bg-neutral-900/20">
                    <BestWorstTimes
                        bestTimes={mockData.bestTimes}
                        worstTimes={mockData.worstTimes}
                        className="h-full"
                    />
                </Card>

                {/* 7. HEATMAP & TRENDS - 2x1 Wide */}
                <Card className="col-span-1 md:col-span-2 lg:col-span-2 bg-neutral-900/20 flex flex-col justify-center">
                    <div className="flex items-center gap-2 mb-2">
                        <Zap className="w-4 h-4 text-amber-400" />
                        <span className="text-xs font-bold text-slate-400 uppercase">Regularność</span>
                    </div>
                    <WeeklyChart data={mockData.weeklyWorkouts} className="h-20" />
                </Card>

                {/* 8. HEATMAP (Long) - Full Width Bottom */}
                <Card className="col-span-1 md:col-span-4 lg:col-span-6 bg-[#030303] border-white/5">
                    <YearlyHeatmap
                        data={mockData.heatmapData}
                        year={heatmapYear}
                        onYearChange={setHeatmapYear}
                    />
                </Card>

            </div>

            {/* Floating Dock Navigation */}
            <FloatingDock activeTab={activeTab} onTabChange={setActiveTab} liveCount={mockData.liveCount} />
        </div>
    )
}
