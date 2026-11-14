import { Button } from "../components/ui";
import { ZynMark } from "../components/icons";

export function SignIn() {
  return (
    <div className="signin-page stack-lg">
      <div className="signin-icon">
        <ZynMark size={48} aria-hidden />
      </div>
      <h2>Sign in with your company account</h2>
      <p className="quiet signin-copy">
        This Zyn server is running in team mode. Sign in to view and review requirements, test specs, and findings.
      </p>
      <div>
        <Button
          variant="primary"
          wide
          onClick={() => {
            window.location.href = "/auth/login";
          }}
        >
          Sign in with company account
        </Button>
      </div>
    </div>
  );
}
