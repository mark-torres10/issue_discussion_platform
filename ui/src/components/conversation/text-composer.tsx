"use client";

import { useState } from "react";
import { SendHorizonal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useUiCopy } from "@/lib/content/content-provider";

interface TextComposerProps {
  disabled: boolean;
  onSend: (text: string) => void;
}

/**
 * Familiar text message box with send button.
 */
export function TextComposer({ disabled, onSend }: TextComposerProps) {
  const copy = useUiCopy();
  const [draft, setDraft] = useState("");

  function submit() {
    const trimmed = draft.trim();
    if (!trimmed || disabled) {
      return;
    }
    onSend(trimmed);
    setDraft("");
  }

  return (
    <div className="flex items-end gap-2">
      <Textarea
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        placeholder={copy.conversation.typeYourResponse}
        aria-label={copy.conversation.typeYourResponse}
        disabled={disabled}
        className="min-h-12 resize-none"
        data-testid="text-composer"
      />
      <Button
        type="button"
        onClick={submit}
        disabled={disabled || draft.trim().length === 0}
        aria-label={copy.conversation.sendMessageAriaLabel}
        data-testid="send-message"
      >
        <SendHorizonal data-icon="inline-start" />
        {copy.conversation.send}
      </Button>
    </div>
  );
}
