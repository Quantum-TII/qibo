#include "tensorflow/core/framework/op_kernel.h"
#include "tensorflow/core/util/work_sharder.h"
#include "apply_gate.h"

namespace tensorflow {

typedef Eigen::ThreadPoolDevice CPUDevice;
typedef Eigen::GpuDevice GPUDevice;

namespace functor {

using thread::ThreadPool;

// CPU specialization
template <typename T>
struct ApplyGateFunctor<CPUDevice, T> {
  void operator()(const OpKernelContext* context, const CPUDevice& d, T* state,
                  const T* gate, int nqubits, int target,
                  const int32* controls, int ncontrols) {
    const int64 nstates = std::pow(2, nqubits);
    const int64 tk = std::pow(2, nqubits - target - 1);

    int64 cktot = 0;
    std::set<int64> cks;
    for (int i = 0; i < ncontrols; i++) {
      int64 ck = std::pow(2, nqubits - controls[i] - 1);
      cks.insert(ck);
      cktot += ck;
    }

    auto DoWork = [&](int64 g, int64 w) {
      for (auto i = g; i < g + tk; i++) {
        bool apply = true;
        for (std::set<int64>::iterator q = cks.begin(); q != cks.end(); q++) {
          if (((int64) i / *q) % 2) {
            apply = false;
            break;
          }
        }

        if (apply) {
          const int64 i1 = i + cktot;
          const int64 i2 = i1 + tk;
          const auto buffer = state[i1];
          state[i1] = gate[0] * state[i1] + gate[1] * state[i2];
          state[i2] = gate[2] * buffer + gate[3] * state[i2];
        }
      }
    };

    const ThreadPool::SchedulingParams p(
        ThreadPool::SchedulingStrategy::kFixedBlockSize, absl::nullopt, 2 * tk);
    auto thread_pool =
        context->device()->tensorflow_cpu_worker_threads()->workers;
    thread_pool->ParallelFor(nstates, p, DoWork);
  }
};

template <typename Device, typename T>
class ApplyGateOp : public OpKernel {
 public:
  explicit ApplyGateOp(OpKernelConstruction* context) : OpKernel(context) {}

  void Compute(OpKernelContext* context) override {
    // grabe the input tensor
    Tensor state = context->input(0);
    const Tensor& gate = context->input(1);
    const Tensor& controls = context->input(4);
    const int nqubits = context->input(2).flat<int32>()(0);
    const int target = context->input(3).flat<int32>()(0);
    const int ncontrols = controls.flat<int32>().size();

    // prevent running on GPU
    OP_REQUIRES(
        context, (std::is_same<Device, CPUDevice>::value == true),
        errors::Unimplemented("ApplyGate operator not implemented for GPU."));

    // call the implementation
    ApplyGateFunctor<Device, T>()(context, context->eigen_device<Device>(),
                                  state.flat<T>().data(),
                                  gate.flat<T>().data(),
                                  nqubits, target,
                                  controls.flat<int32>().data(),
                                  ncontrols);

    context->set_output(0, state);
  }
};

// Register the CPU kernels.
#define REGISTER_CPU(T)                                            \
  REGISTER_KERNEL_BUILDER(                                         \
      Name("ApplyGate").Device(DEVICE_CPU).TypeConstraint<T>("T"), \
      ApplyGateOp<CPUDevice, T>);
REGISTER_CPU(complex64);
REGISTER_CPU(complex128);

// Register the GPU kernels.
#define REGISTER_GPU(T)                                            \
  extern template struct ApplyGateFunctor<GPUDevice, T>;           \
  REGISTER_KERNEL_BUILDER(                                         \
      Name("ApplyGate").Device(DEVICE_GPU).TypeConstraint<T>("T"), \
      ApplyGateOp<GPUDevice, T>);
REGISTER_GPU(complex64);
REGISTER_GPU(complex128);
}  // namespace functor
}  // namespace tensorflow
