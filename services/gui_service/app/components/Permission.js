import { useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useRouter } from "next/navigation";

// Usage: <Permission permission="approve_user"> <Button>Approve</Button> </Permission>
// Usage with fallback: <Permission permission="approve_user" fallback> <Text>No permission</Text> </Permission>
export default function Permission({ permission, children, fallback = false }) {
  const router = useRouter();
  const { hasPermission, isLoading, user } = useAuth();
  const userHasPermission = hasPermission(permission);

  useEffect(() => {
    if (!isLoading && !userHasPermission && !fallback) {
      // Redirect if not using fallback UI
     return;
    }
  }, [user, isLoading, userHasPermission, router, fallback]);

  if (isLoading) return null;
  if (!userHasPermission) {
    if (fallback) return null; // fallback UI can be handled by parent
    return null;
  }
  return <>{children}</>;
}
