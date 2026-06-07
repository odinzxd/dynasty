import React from "react";

export default function BrandLogo({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 160 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Dynasty 8 logo"
    >
      <circle cx="118" cy="26" r="22" fill="#F9CF4E" />
      <path d="M16 64L44 36L84 64V98H16V64Z" fill="#1E5933" />
      <path d="M42 98H72V68L56 52L42 68V98Z" fill="#0F3420" />
      <rect x="26" y="72" width="24" height="16" rx="4" fill="#F9CF4E" />
      <text x="18" y="116" fill="#F6F6F6" fontFamily="Inter, sans-serif" fontWeight="700" fontSize="26">
        Dynasty
      </text>
      <text x="112" y="116" fill="#F9CF4E" fontFamily="Inter, sans-serif" fontWeight="800" fontSize="32">
        8
      </text>
    </svg>
  );
}
