import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "@/app/page";

describe("HomePage", () => {
  it("explains the product proposition with a single primary heading", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "See the distance between where you are and where you want to go.",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Transparent scoring")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Building the system of trust" })).toBeInTheDocument();
  });
});
