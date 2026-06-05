import React, { useState, useEffect, useRef } from "react";
import { useUpdateNodeInternals } from "reactflow";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const TextNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const updateNodeInternals = useUpdateNodeInternals();

  const [text, setText] = useState(data?.text || "");
  const [variables, setVariables] = useState([]);
  const [dimensions, setDimensions] = useState({ width: 220, height: 80 });
  const textareaRef = useRef(null);

  useEffect(() => {
    const regex = /{{\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*}}/g;
    const matches = [...text.matchAll(regex)];
    const vars = matches.map((match) => ({
      id: match[1],
    }));

    setVariables(vars);
  }, [text]);

  useEffect(() => {
    if (id) {
      updateNodeInternals(id);
    }
  }, [id, variables, updateNodeInternals]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      
      const calculatedHeight = Math.max(80, scrollHeight + 4);

      const lines = text.split("\n");
      const longestLineLength = lines.reduce(
        (max, line) => (line.length > max ? line.length : max),
        0
      );
      const calculatedWidth = Math.min(450, Math.max(220, longestLineLength * 8 + 24));

      setDimensions({ width: calculatedWidth, height: calculatedHeight });
    }
  }, [text]);

  const handleTextChange = (e) => {
    const val = e.target.value;
    setText(val);
    if (id) {
      updateNodeField(id, "text", val);
    }
  };

  return (
    <BaseNode
      title="Text Node"
      inputs={variables}
      outputs={[{ id: "output" }]}
    >
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleTextChange}
        placeholder="Enter text with {{variables}}"
        style={{
          width: `${dimensions.width}px`,
          height: `${dimensions.height}px`,
        }}
        className="p-2 rounded bg-slate-800 text-white resize-none border border-slate-700 focus:outline-none focus:border-cyan-500 transition-colors"
      />
    </BaseNode>
  );
};

export default TextNode;