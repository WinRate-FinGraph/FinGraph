import { z } from "zod";

export const simulationSchema = z.object({
    sender_account_id: z.string().min(1, "Sender account is required"),
    receiver_account_id: z.string().min(1, "Receiver account is required"),
    device_id: z.string().min(1, "Device is required"),
    merchant_id: z.string().min(1, "Merchant is required"),
    amount: z.coerce
        .number()
        .positive("Amount must be greater than 0")
        .min(1000, "Minimum amount is IDR 1,000"),
    currency: z.string().min(1, "Currency is required"),
    channel: z.string().min(1, "Channel is required"),
    source_country: z.string().min(2, "Source country is required"),
    destination_country: z.string().min(2, "Destination country is required"),
    ip_address: z.string().optional(),
});

export type SimulationFormInput = z.input<typeof simulationSchema>;
export type SimulationFormValues = z.output<typeof simulationSchema>;