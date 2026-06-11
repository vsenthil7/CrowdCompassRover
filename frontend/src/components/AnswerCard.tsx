import type { ChatAnswer } from "../lib/types";
import { languageLabel } from "../lib/display";

interface Props {
  answer: ChatAnswer;
}

export function AnswerCard({ answer }: Props) {
  return (
    <section className="answer" data-testid="answer-card" role="status" aria-live="polite" aria-label="AI answer">
      <h2 className="answer__head">Concierge · {languageLabel(answer.language)}</h2>
      <div>{answer.answer}</div>
    </section>
  );
}
