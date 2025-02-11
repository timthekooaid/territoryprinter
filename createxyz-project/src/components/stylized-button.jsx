"use client";
import React from "react";

function StylizedButton({ text, onClick }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded text-black font-semibold bg-[#A3E636] border border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
    >
      {text}
    </button>
  );
}

function StylizedButtonStory() {
  return (
    <div className="p-4 space-y-4">
      <StylizedButton
        text="Click me!"
        onClick={() => alert("Button clicked!")}
      />
      <StylizedButton text="Submit" onClick={() => alert("Submitted!")} />
      <StylizedButton text="Cancel" onClick={() => alert("Cancelled!")} />
    </div>
  );
}

export default StylizedButton;