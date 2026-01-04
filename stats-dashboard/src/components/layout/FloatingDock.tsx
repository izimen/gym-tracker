import { cn } from "@/lib/utils"
import { BarChart2, Home, Settings, User } from "lucide-react"

interface FloatingDockProps {
    activeTab: string
    onTabChange: (tab: string) => void
    liveCount: number
}

export function FloatingDock({ activeTab, onTabChange, liveCount }: FloatingDockProps) {
    const tabs = [
        { id: "home", icon: Home, label: "Home" },
        { id: "stats", icon: BarChart2, label: "Stats" },
        { id: "profile", icon: User, label: "Profile" },
        { id: "settings", icon: Settings, label: "More" },
    ]

    return (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
            <div className="flex items-center gap-2 p-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-2xl shadow-[0_0_50px_-12px_rgba(0,0,0,0.5)]">
                {tabs.map((tab) => {
                    const isActive = activeTab === tab.id

                    return (
                        <button
                            key={tab.id}
                            onClick={() => onTabChange(tab.id)}
                            className={cn(
                                "relative group flex items-center justify-center w-12 h-12 rounded-full transition-all duration-300",
                                isActive
                                    ? "bg-white text-black scale-110 shadow-[0_0_20px_-5px_rgba(255,255,255,0.5)]"
                                    : "text-neutral-400 hover:text-white hover:bg-white/10"
                            )}
                        >
                            <tab.icon className={cn("w-5 h-5 transition-transform", isActive ? "scale-110" : "group-hover:scale-110")} />

                            {/* Live Indicator on Stats Tab */}
                            {tab.id === "stats" && !isActive && (
                                <span className="absolute top-2 right-2.5 w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                            )}

                            {/* Label Tooltip */}
                            <span className="absolute -top-10 bg-black/80 text-white text-[10px] px-2 py-1 rounded border border-white/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap backdrop-blur-md">
                                {tab.label}
                            </span>
                        </button>
                    )
                })}
            </div>
        </div>
    )
}
