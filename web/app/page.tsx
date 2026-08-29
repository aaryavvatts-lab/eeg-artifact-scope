import Scope from '@/components/Scope';

// A server component wrapping the client one. Next 15.5.4 fails to resolve a
// client component used directly as a page's default export during `output:
// "export"` ("Could not find the module ... in the React Client Manifest"),
// and this thin wrapper is the documented way around it.
export default function Page() {
  return <Scope />;
}
