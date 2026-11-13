import { render, screen } from "@testing-library/react";
import { Diff, Highlight, Msg } from "./ui";

describe("design system components", () => {
  it("marks quoted evidence inside the text", () => {
    const { container } = render(<p><Highlight text="The gauge shall update quickly." evidence="quickly" /></p>);
    expect(container.querySelector("mark")?.textContent).toBe("quickly");
  });

  it("leaves text alone when the evidence is not in it", () => {
    const { container } = render(<p><Highlight text="Shall update." evidence="missing" /></p>);
    expect(container.querySelector("mark")).toBeNull();
  });

  it("shows deleted and inserted words with their classes", () => {
    const { container } = render(<p><Diff ops={[["equal", "lit in"], ["delete", "1"], ["insert", "2"], ["equal", "s"]]} /></p>);
    expect(container.querySelector(".del")?.textContent).toBe("1");
    expect(container.querySelector(".ins")?.textContent).toBe("2");
  });

  it("marks failed code checks as alerts for screen readers", () => {
    render(<Msg tone="bad">Ungrounded</Msg>);
    expect(screen.getByRole("alert").textContent).toContain("Ungrounded");
  });
});
