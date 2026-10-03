import { redirect } from "next/navigation";
export default async function LegacyTransactionDetail({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; redirect(`/dashboard/payments/${id}`); }
