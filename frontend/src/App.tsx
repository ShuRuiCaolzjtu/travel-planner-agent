import { useSessionStore } from "./store/sessionStore";
import CityInput from "./pages/CityInput";
import CardFlow from "./pages/CardFlow";
import ConstraintChat from "./pages/ConstraintChat";
import ResultPage from "./pages/ResultPage";

export default function App() {
  const { phase } = useSessionStore();

  if (phase === "city_input") return <CityInput />;
  if (phase === "card_flow") return (
    <div>
      <header className="text-center pt-4 pb-2">
        <h1 className="text-lg font-bold text-gray-700">探索大理</h1>
      </header>
      <CardFlow />
    </div>
  );
  if (phase === "constraint" || phase === "planning") return (
    <div>
      <header className="text-center pt-4 pb-2">
        <h1 className="text-lg font-bold text-gray-700">你的偏好</h1>
      </header>
      <ConstraintChat />
    </div>
  );
  if (phase === "result" || phase === "adjust") return <ResultPage />;

  return <CityInput />;
}
