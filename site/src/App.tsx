import { AnimatePresence, motion } from "motion/react";
import { useLayoutEffect, useState } from "react";
import { Toaster } from "sonner";
import { Sprite } from "./components/ui";
import { CheckerBand } from "./components/bands";
import { Footer, Nav, Palette, useTheme } from "./sections/Chrome";
import { Hero } from "./sections/Hero";
import { How } from "./sections/How";
import { Problem } from "./sections/Problem";
import { Proof } from "./sections/Proof";
import { Contribute } from "./sections/Start";
import { Tools } from "./sections/Tools";
import { Work } from "./sections/Why";
import { Teams } from "./sections/Teams";
import { Roadmap } from "./sections/Roadmap";
import { DocPage } from "./docs/DocPage";
import { bySlug, HOME } from "./docs/docs";
import { scrollToHash, usePage } from "./router";

export default function App() {
  const [theme, setTheme] = useTheme();
  const [palette, setPalette] = useState(false);
  const page = usePage();
  const doc = bySlug.get(page);

  // New page: start at the top, or at the #section it asks for. Refresh scroll-driven animations.
  useLayoutEffect(() => {
    if (!doc) document.title = page === "" ? "Zyn: checks AI engineering work before you sign" : "Page not found: Zyn";
  }, [page, doc]);
  // When the old page has faded out, place the new one: at its #section, or at the top.
  const place = () => {
    if (!scrollToHash(window.location.hash, true)) window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
  };

  return (
    <>
      <Sprite />
      <a className="skip" href="#top">
        Skip to content
      </a>
      <Nav theme={theme} onTheme={setTheme} onPalette={() => setPalette(true)} />
      <AnimatePresence mode="wait" initial={false} onExitComplete={place}>
        <motion.main
          key={page || "home"}
          id="top"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, ease: [0.165, 0.84, 0.44, 1] }}
        >
          {doc ? (
            <DocPage meta={doc} />
          ) : page === "" ? (
            <>
              <Hero />
              <CheckerBand />
              <Problem />
              <How />
              <Proof />
              <Tools />
              <Teams />
              <Work />
              <Roadmap />
              <Contribute />
            </>
          ) : (
            <NotFound />
          )}
        </motion.main>
      </AnimatePresence>
      <Footer />
      <Palette open={palette} setOpen={setPalette} setTheme={setTheme} />
      <Toaster
        position="bottom-center"
        toastOptions={{ unstyled: true, classNames: { toast: "slip", title: "slip__title", description: "slip__desc" } }}
      />
    </>
  );
}

function NotFound() {
  return (
    <section className="section">
      <div className="wrap">
        <h1 className="headline">
          <span className="headline__plain">There is no page here.</span>
        </h1>
        <p className="body">
          The address may be old. <a className="link" href={HOME}>Go to the Zyn home page</a> or{" "}
          <a className="link" href={`${import.meta.env.BASE_URL}docs`}>open the docs</a>.
        </p>
      </div>
    </section>
  );
}
