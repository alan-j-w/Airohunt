import React from "react";
import { Handle, Position } from "reactflow";

const BaseNode = ({
    title,
    children,
    inputs = [],
    outputs = [],
    headerBg = "bg-cyan-500",
    headerTextColor = "text-black",
    borderColor = "border-cyan-500/40"
}) => {
    return (
        <div className={`bg-slate-900 border ${borderColor} shadow-2xl rounded-2xl min-w-[240px] text-white overflow-hidden transition-all duration-300 hover:shadow-cyan-950/20`}>

            {/* NODE HEADER */}
            <div className={`${headerBg} ${headerTextColor} font-black uppercase tracking-wider text-[11px] px-4 py-2.5 flex items-center justify-between`}>
                <span>{title}</span>
                <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse"></span>
            </div>

            {/* NODE CONTENT */}
            <div className="p-4 bg-slate-900/60 backdrop-blur-sm space-y-3">
                {children}
            </div>

            {/* INPUT PORT HANDLES */}
            {inputs.map((input, index) => (
                <div key={input.id} className="relative">
                    <Handle
                        type="target"
                        position={Position.Left}
                        id={input.id}
                        style={{
                            top: 55 + index * 32,
                            background: "#06b6d4",
                            border: "2px solid #020617",
                            width: "10px",
                            height: "10px",
                        }}
                    />
                    {input.label && (
                        <span className="absolute left-2.5 text-[9px] text-slate-500 font-bold uppercase tracking-widest pointer-events-none" style={{ top: 48 + index * 32 }}>
                            {input.label}
                        </span>
                    )}
                </div>
            ))}

            {/* OUTPUT PORT HANDLES */}
            {outputs.map((output, index) => (
                <div key={output.id} className="relative">
                    <Handle
                        type="source"
                        position={Position.Right}
                        id={output.id}
                        style={{
                            top: 55 + index * 32,
                            background: "#10b981",
                            border: "2px solid #020617",
                            width: "10px",
                            height: "10px",
                        }}
                    />
                    {output.label && (
                        <span className="absolute right-2.5 text-[9px] text-slate-500 font-bold uppercase tracking-widest text-right pointer-events-none" style={{ top: 48 + index * 32 }}>
                            {output.label}
                        </span>
                    )}
                </div>
            ))}
        </div>
    );
};

export default BaseNode;