import { Card } from './Card';
import { OptionButton } from './OptionButton';

/** Mirrors the contract's `Dilemma`: option effects stay hidden until the end of the run. */
export interface DilemmaCardData {
  id: string;
  title: string;
  prompt: string;
  options: readonly { id: string; label: string }[];
}

export interface DilemmaCardProps {
  dilemma: DilemmaCardData;
  selectedOptionId?: string | null;
  onSelect?: (optionId: string) => void;
  /** Locks every option, for example once the decision has been sent. */
  disabled?: boolean;
  eyebrow?: string;
  headingLevel?: 2 | 3 | 4;
}

const MARKERS = 'ABCDEFGH';

export function DilemmaCard({
  dilemma,
  selectedOptionId = null,
  onSelect,
  disabled = false,
  eyebrow,
  headingLevel = 2,
}: DilemmaCardProps) {
  return (
    <Card
      title={dilemma.title}
      headingLevel={headingLevel}
      tone={selectedOptionId === null ? 'default' : 'highlight'}
      {...(eyebrow !== undefined && { eyebrow })}
    >
      <p className="mb-4 text-body text-ink">{dilemma.prompt}</p>
      <div role="group" aria-label={`Opciones: ${dilemma.title}`} className="flex flex-col gap-2">
        {dilemma.options.map((option, index) => (
          <OptionButton
            key={option.id}
            label={option.label}
            marker={MARKERS.charAt(index)}
            selected={option.id === selectedOptionId}
            disabled={disabled}
            onSelect={() => onSelect?.(option.id)}
          />
        ))}
      </div>
    </Card>
  );
}
