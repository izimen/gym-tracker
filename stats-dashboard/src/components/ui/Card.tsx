import { cn } from "@/lib/utils"

interface CardProps {
    children: React.ReactNode
    className?: string
    noPadding?: boolean
}

export function Card({ children, className, noPadding = false }: CardProps) {
    return (
        <div
            className={cn(
                "glass-panel rounded-[2rem] overflow-hidden transition-all duration-500",
                "border border-white/5 bg-black/40 backdrop-blur-3xl", /* True Deep Black Glass */
                !noPadding && "p-6",
                className
            )}
        >
            {children}
        </div>
    )
}
