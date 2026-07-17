"use client";

/**
 * Inline SVG logos for AI providers.
 * Kept minimal and monochrome to match the app's style.
 */

const iconClass = "h-4 w-4 flex-shrink-0";

export function OpenAILogo({ className = iconClass }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" />
    </svg>
  );
}

export function AnthropicLogo({ className = iconClass }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.304 3.541h-3.48l6.157 16.918h3.48L17.304 3.541zm-10.609 0L.539 20.459H4.02l1.27-3.493h6.39l1.27 3.493h3.482L10.275 3.541H6.695zm.582 10.63l2.207-6.07 2.207 6.07H7.277z" />
    </svg>
  );
}

export function GoogleAILogo({ className = iconClass }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.8" />
      <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.6" />
      <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.8" />
    </svg>
  );
}

export function AWSLogo({ className = iconClass }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M6.763 10.036c0 .296.032.535.088.71.064.176.144.368.256.576.04.063.056.127.056.183 0 .08-.048.16-.152.24l-.503.335a.383.383 0 0 1-.208.072c-.08 0-.16-.04-.239-.112a2.47 2.47 0 0 1-.287-.374 6.18 6.18 0 0 1-.248-.467c-.622.734-1.405 1.101-2.347 1.101-.67 0-1.205-.191-1.596-.574-.391-.384-.59-.894-.59-1.533 0-.678.239-1.23.726-1.644.487-.415 1.133-.623 1.955-.623.272 0 .551.024.846.064.296.04.6.104.918.176v-.583c0-.607-.127-1.03-.375-1.277-.255-.248-.686-.367-1.3-.367-.28 0-.568.031-.863.103a6.395 6.395 0 0 0-.862.279 2.3 2.3 0 0 1-.28.104.488.488 0 0 1-.127.023c-.112 0-.168-.08-.168-.247v-.391c0-.128.016-.224.056-.28a.597.597 0 0 1 .224-.167 4.598 4.598 0 0 1 1.005-.36 4.84 4.84 0 0 1 1.246-.151c.95 0 1.644.216 2.091.647.44.43.662 1.085.662 1.963v2.586zm-3.24 1.214c.263 0 .534-.048.822-.144.287-.096.543-.271.758-.51.128-.152.224-.32.272-.512.047-.191.08-.423.08-.694v-.335a6.66 6.66 0 0 0-.735-.136 6.02 6.02 0 0 0-.75-.048c-.535 0-.926.104-1.19.32-.263.215-.39.518-.39.917 0 .375.095.655.295.846.191.2.47.296.838.296z" />
      <path d="M18.12 12.03c-.08 0-.136-.008-.176-.032-.04-.032-.072-.096-.112-.2l-1.252-4.12a1.835 1.835 0 0 1-.08-.343c0-.136.064-.216.192-.216h.782c.088 0 .144.008.184.032.04.032.072.096.104.2l.895 3.527.83-3.527c.024-.112.056-.168.096-.2a.353.353 0 0 1 .192-.032h.639c.088 0 .152.008.192.032.04.032.072.096.096.2l.838 3.567.926-3.567c.032-.112.072-.168.104-.2a.346.346 0 0 1 .184-.032h.742c.128 0 .2.072.2.216 0 .04-.009.08-.017.128a1.242 1.242 0 0 1-.064.224l-1.284 4.12c-.04.112-.072.168-.112.2a.35.35 0 0 1-.176.032h-.686c-.088 0-.152-.008-.192-.04-.04-.032-.072-.096-.096-.208l-.822-3.43-.814 3.422c-.024.112-.056.176-.096.208-.04.032-.112.04-.192.04h-.686z" />
    </svg>
  );
}

export function AzureLogo({ className = iconClass }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M5.483 21.3H18.67L12.074 9.516l5.214-7.518H5.483l-2.69 7.518L5.483 21.3zm0 0" opacity="0.8" />
      <path d="M9.98 2H5.483L2.794 9.516l6.684 11.784H18.67L9.98 2z" opacity="0.6" />
    </svg>
  );
}

export function OllamaLogo({ className = iconClass }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <circle cx="12" cy="8" r="5" opacity="0.8" />
      <path d="M12 14c-4.418 0-8 2.239-8 5v2h16v-2c0-2.761-3.582-5-8-5z" opacity="0.6" />
      <circle cx="10" cy="7" r="1" fill="white" opacity="0.9" />
      <circle cx="14" cy="7" r="1" fill="white" opacity="0.9" />
    </svg>
  );
}

export function GroqLogo({ className = iconClass }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" />
    </svg>
  );
}

export function MistralLogo({ className = iconClass }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <rect x="2" y="3" width="4" height="4" opacity="1" />
      <rect x="18" y="3" width="4" height="4" opacity="1" />
      <rect x="2" y="10" width="4" height="4" opacity="0.8" />
      <rect x="10" y="10" width="4" height="4" opacity="0.8" />
      <rect x="18" y="10" width="4" height="4" opacity="0.8" />
      <rect x="2" y="17" width="4" height="4" opacity="0.6" />
      <rect x="6" y="17" width="4" height="4" opacity="0.6" />
      <rect x="10" y="17" width="4" height="4" opacity="0.6" />
      <rect x="14" y="17" width="4" height="4" opacity="0.6" />
      <rect x="18" y="17" width="4" height="4" opacity="0.6" />
    </svg>
  );
}

export const PROVIDER_LOGOS: Record<string, React.ComponentType<{ className?: string }>> = {
  openai: OpenAILogo,
  anthropic: AnthropicLogo,
  google_ai: GoogleAILogo,
  aws_bedrock: AWSLogo,
  azure_openai: AzureLogo,
  ollama: OllamaLogo,
  groq: GroqLogo,
  mistral: MistralLogo,
};
