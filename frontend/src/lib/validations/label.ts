import { z } from "zod";

export const labelSchema = z.object({
    transaction_id: z.string().min(1, "Transaction is required"),
    label: z.enum(["fraud", "legitimate", "suspicious"], {
        message: "Label must be fraud, legitimate, or suspicious",
    }),
    labelled_by: z.string().min(2, "Analyst name is required"),
    notes: z.string().optional(),
});

export type LabelFormValues = z.infer<typeof labelSchema>;