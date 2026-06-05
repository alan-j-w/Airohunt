// submit.js

import Swal from "sweetalert2";
import { useStore } from "./store";

export const SubmitButton = () => {

    const nodes = useStore((state) => state.nodes);

    const edges = useStore((state) => state.edges);

    const handleSubmit = async () => {

        try {

            const response = await fetch(
                "http://127.0.0.1:8000/pipelines/parse",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        nodes,
                        edges,
                    }),
                }
            );

            const data = await response.json();

            Swal.fire({
                title: "Pipeline Analysis",
                html: `
          <div style="text-align:left">
            <p><b>Nodes:</b> ${data.num_nodes}</p>
            <p><b>Edges:</b> ${data.num_edges}</p>
            <p><b>Is DAG:</b> ${data.is_dag}</p>
          </div>
        `,
                icon: "success",
                background: "#0f172a",
                color: "#fff",
                confirmButtonColor: "#06b6d4",
            });

        } catch (error) {

            Swal.fire({
                title: "Error",
                text: "Backend connection failed",
                icon: "error",
            });

            console.error(error);
        }
    };

    return (
        <div className="flex justify-center mt-4">

            <button
                onClick={handleSubmit}
                className="
          bg-cyan-500
          hover:bg-cyan-400
          text-black
          font-bold
          px-6
          py-3
          rounded-xl
          transition-all
          duration-300
          hover:scale-105
        "
            >
                Submit Pipeline
            </button>

        </div>
    );
};