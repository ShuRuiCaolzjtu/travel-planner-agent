import { useSessionStore } from "../store/sessionStore";
import CardDeck from "../components/CardDeck";
import ProgressBar from "../components/ProgressBar";

const TOTAL_CARDS = 30;

export default function CardFlow() {
  const { cards, likeCount, scoredCount, scoreCard, setPhase, error } =
    useSessionStore();

  const handleSwipeRight = async (poiId: string) => {
    await scoreCard(poiId, 5, "swipe_right");
  };

  const handleSwipeLeft = async (poiId: string) => {
    await scoreCard(poiId, 1, "swipe_left");
  };

  const handleSwipeUp = async (poiId: string) => {
    await scoreCard(poiId, 3, "swipe_up");
  };

  const handleSwipeDown = async (poiId: string) => {
    await scoreCard(poiId, 0, "swipe_down");
  };

  const handleStar = async (poiId: string, score: number) => {
    await scoreCard(poiId, score, "tap_star");
  };

  return (
    <div className="flex flex-col items-center gap-4 py-8">
      {error && (
        <div className="bg-red-50 text-red-600 text-sm px-4 py-2 rounded-lg max-w-sm text-center">
          加载失败: {error}
        </div>
      )}
      <ProgressBar current={scoredCount} total={TOTAL_CARDS} />

      <CardDeck
        cards={cards}
        onSwipeLeft={handleSwipeLeft}
        onSwipeRight={handleSwipeRight}
        onSwipeUp={handleSwipeUp}
        onSwipeDown={handleSwipeDown}
        onStar={handleStar}
      />

      <div className="flex gap-8 text-sm text-gray-400 mt-2">
        <span className="flex items-center gap-1">👈 不感兴趣</span>
        <span className="flex items-center gap-1">👆 详情</span>
        <span className="flex items-center gap-1">👉 想去</span>
      </div>

      <button
        onClick={() => setPhase("constraint")}
        className="mt-4 bg-gradient-to-r from-amber-500 to-rose-500 text-white px-8 py-3 rounded-xl font-bold shadow-lg hover:shadow-xl transition"
      >
        开始排程 ({likeCount}个想去)
      </button>
    </div>
  );
}
